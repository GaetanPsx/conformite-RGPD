"""Fusion en profil combine + rendu HTML + export telechargeable (FR-011/012/001b).

Aucune fonction de ce module ne DOIT jamais introduire de champ de score/niveau de risque de
conformite agrege (FR-014) : seule la liste individuelle de NonConformite est dans le scope.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models.depot import DepotCible, ModeEntree
from src.models.detection_rgpd import DetectionRgpd
from src.models.documentation import DocumentationFournie
from src.models.non_conformite import NonConformite
from src.models.profil_aiact import ProfilAiAct
from src.models.rapport import ProfilProjetCombine, RapportFinal

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def combiner(
    mode_entree: ModeEntree,
    depot: DepotCible | None,
    documentation: DocumentationFournie | None,
    profil_aiact: ProfilAiAct,
    detections_rgpd: list[DetectionRgpd],
    non_conformites: list[NonConformite] | None = None,
    appels_llm: int = 0,
    tailles_envoyees: list[int] | None = None,
    arborescence_tronquee: bool = False,
) -> ProfilProjetCombine:
    """Fusionne les resultats AI Act / RGPD / non-conformites en un profil unique (FR-011)."""
    non_conformites = non_conformites or []
    tailles_envoyees = tailles_envoyees or []
    avertissements: list[str] = []

    if mode_entree.source_ignoree:
        avertissements.append(
            "entrée documentation ignorée au profit du dépôt (les deux entrées ont été fournies)"
        )
    if arborescence_tronquee:
        avertissements.append(
            "liste de fichiers du dépôt incomplète (arborescence GitHub tronquée)"
        )
    if not detections_rgpd:
        avertissements.append("aucune donnée personnelle détectée")
    if not non_conformites:
        avertissements.append("aucune non-conformité identifiée")
    if profil_aiact.echec:
        avertissements.append("l'analyse AI Act a échoué pour cette évaluation")
    if not profil_aiact.fichiers_source and not detections_rgpd:
        avertissements.append("aucun élément pertinent (AI Act ou RGPD) détecté")

    return ProfilProjetCombine(
        mode_entree=mode_entree,
        depot=depot,
        documentation=documentation,
        profil_aiact=profil_aiact,
        detections_rgpd=detections_rgpd,
        non_conformites=non_conformites,
        appels_llm_effectues=appels_llm,
        taille_envoyee_par_appel=tailles_envoyees,
        avertissements=avertissements,
    )


def rendre_html(profil: ProfilProjetCombine) -> RapportFinal:
    """Rend le rapport HTML structure a partir du profil combine (FR-012).

    Ne construit jamais de champ de score/niveau de risque agrege (FR-014).
    """
    citations = sorted(
        {
            *profil.profil_aiact.passages_utilises,
            *(nc.passage_source for nc in profil.non_conformites),
        }
    )
    corps_html = _env.get_template("rapport_corps.html").render(profil=profil, citations=citations)
    html = _env.get_template("rapport.html").render(corps_html=corps_html)
    return RapportFinal(
        profil_combine=profil,
        citations=citations,
        avertissements=profil.avertissements,
        telechargeable=True,
        html=html,
    )


def envelopper_telechargement(corps_html: str) -> str:
    """Enveloppe le corps du rapport (deja rendu pour l'affichage) dans le gabarit de
    telechargement, sans aucune ecriture serveur ni recalcul du pipeline (FR-001b, FR-017) :
    le corps telecharge est ainsi identique au corps affiche dans la reponse `POST /evaluate`
    qui l'a produit."""
    return _env.get_template("rapport_telecharge.html").render(corps_html=corps_html)
