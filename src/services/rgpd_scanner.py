"""Detection RGPD par motifs deterministes, sans appel LLM (FR-010).

Une expression reguliere par categorie (identite, contact, identifiant_national, sante,
biometrie, origine_croyances). Le masquage (FR-010a) est applique immediatement apres chaque
detection via `rgpd_masking.masquer`, avant toute autre etape.
"""

from __future__ import annotations

import re

from src.models.detection_rgpd import CategorieRgpd, DetectionRgpd
from src.models.non_conformite import NonConformite, OrigineNonConformite
from src.models.selection import SelectionRgpd
from src.services.legal_rag import retriever
from src.services.rgpd_masking import masquer

# Seuil de pertinence minimal (score de similarite cosinus, retriever.rechercher) en dessous
# duquel aucune NonConformite n'est produite pour une categorie RGPD detectee : un aspect sans
# passage suffisamment pertinent n'est jamais transforme en non-conformite inventee (FR-013,
# FR-019, Edge Cases US2 Acceptance Scenario 4).
SEUIL_PERTINENCE_NON_CONFORMITE = 0.35

# Requete RAG (langage naturel) associee a chaque categorie RGPD, utilisee pour retrouver le
# passage legal le plus pertinent justifiant un point de non-conformite potentiel.
REQUETES_RAG_PAR_CATEGORIE: dict[CategorieRgpd, str] = {
    CategorieRgpd.IDENTITE: "traitement de donnees d'identite nom et prenom complet",
    CategorieRgpd.CONTACT: "traitement de coordonnees de contact email et telephone",
    CategorieRgpd.IDENTIFIANT_NATIONAL: (
        "traitement d'un numero d'identification national, garanties appropriees"
    ),
    CategorieRgpd.SANTE: (
        "traitement de donnees de sante sans base legale explicite, categories particulieres "
        "de donnees"
    ),
    CategorieRgpd.BIOMETRIE: (
        "traitement de donnees biometriques aux fins d'identification unique d'une personne"
    ),
    CategorieRgpd.ORIGINE_CROYANCES: (
        "traitement de donnees revelant l'origine ethnique ou raciale ou les convictions "
        "religieuses"
    ),
}

DESCRIPTIONS_PAR_CATEGORIE: dict[CategorieRgpd, str] = {
    CategorieRgpd.IDENTITE: "Des données d'identité (nom, prénom) ont été détectées",
    CategorieRgpd.CONTACT: "Des coordonnées de contact (email, téléphone) ont été détectées",
    CategorieRgpd.IDENTIFIANT_NATIONAL: (
        "Un identifiant national a été détecté"
    ),
    CategorieRgpd.SANTE: "Des données de santé ont été détectées",
    CategorieRgpd.BIOMETRIE: "Des données biométriques ont été détectées",
    CategorieRgpd.ORIGINE_CROYANCES: (
        "Des données révélant une origine ou une croyance ont été détectées"
    ),
}

# Chaque motif est nomme pour l'audit (DetectionRgpd.motif, Principe III).
PATTERNS: list[tuple[CategorieRgpd, str, re.Pattern]] = [
    (
        CategorieRgpd.CONTACT,
        "email_rfc5322_simplifie",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ),
    (
        CategorieRgpd.CONTACT,
        "telephone_fr",
        re.compile(r"(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}"),
    ),
    (
        CategorieRgpd.IDENTIFIANT_NATIONAL,
        "numero_securite_sociale_fr",
        re.compile(r"\b[12]\d{2}(?:0[1-9]|1[0-2])\d{2}\d{3}\d{3}\d{2}\b"),
    ),
    (
        CategorieRgpd.IDENTITE,
        "colonne_nom_prenom",
        re.compile(
            r"\b(?:nom_complet|full_name|nom_prenom|last_name|first_name)\b\s*[:=]\s*"
            r"['\"]?([A-Z][a-zA-Zàâäéèêëïîôöùûüç'\- ]{2,60})['\"]?"
        ),
    ),
    (
        CategorieRgpd.SANTE,
        "mot_cle_sante",
        re.compile(
            r"(?i)\b(diagnostic|pathologie|maladie|traitement_medical|dossier_medical|"
            r"health_record|medical_condition|numero_secu_sante)\b"
        ),
    ),
    (
        CategorieRgpd.BIOMETRIE,
        "mot_cle_biometrie",
        re.compile(
            r"(?i)\b(empreinte_digitale|fingerprint|reconnaissance_faciale|face_id|"
            r"iris_scan|donnee_biometrique|biometric_template)\b"
        ),
    ),
    (
        CategorieRgpd.ORIGINE_CROYANCES,
        "mot_cle_origine_croyances",
        re.compile(
            r"(?i)\b(origine_ethnique|religion|appartenance_religieuse|opinion_politique|"
            r"ethnic_origin|croyance_religieuse)\b"
        ),
    ),
]


def scanner(selection: SelectionRgpd) -> list[DetectionRgpd]:
    """Scanne le contenu de `selection` par expressions regulieres, sans appel LLM (FR-010)."""
    detections: list[DetectionRgpd] = []
    for fichier_avec_contenu in selection.fichiers:
        source = _nom_source(fichier_avec_contenu)
        contenu = fichier_avec_contenu.contenu
        for categorie, nom_motif, pattern in PATTERNS:
            for match in pattern.finditer(contenu):
                valeur = match.group(1) if match.groups() else match.group(0)
                detections.append(
                    DetectionRgpd(
                        categorie=categorie,
                        source=source,
                        motif=nom_motif,
                        extrait_masque=masquer(categorie, valeur),
                    )
                )
    return detections


def _nom_source(fichier_avec_contenu) -> str:
    fichier = fichier_avec_contenu.fichier
    chemin = getattr(fichier, "chemin", None)
    if chemin:
        return chemin
    return "documentation fournie"


def associer_non_conformites(detections: list[DetectionRgpd]) -> list[NonConformite]:
    """Associe chaque categorie RGPD detectee a un passage RAG effectivement recupere,
    produisant une NonConformite (`origine="detection_rgpd"`) uniquement quand un passage
    suffisamment pertinent existe (FR-013/FR-019). Un aspect sans passage suffisamment pertinent
    n'est jamais transforme en non-conformite inventee (Edge Cases, US2 Acceptance Scenario 4)."""
    categories_detectees = {d.categorie for d in detections}
    non_conformites: list[NonConformite] = []
    for categorie in categories_detectees:
        requete = REQUETES_RAG_PAR_CATEGORIE.get(categorie)
        if not requete:
            continue
        passages = retriever.rechercher(requete, top_n=1)
        if not passages or passages[0].score_pertinence < SEUIL_PERTINENCE_NON_CONFORMITE:
            continue
        non_conformites.append(
            NonConformite(
                description=DESCRIPTIONS_PAR_CATEGORIE.get(
                    categorie, f"Des données de catégorie '{categorie.value}' ont été détectées"
                ),
                passage_source=passages[0].id_reference,
                origine=OrigineNonConformite.DETECTION_RGPD,
            )
        )
    return non_conformites
