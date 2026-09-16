"""Masquage deterministe des extraits detectes, par categorie RGPD (FR-010a, research.md §5).

Applique immediatement apres chaque detection, avant toute autre etape du pipeline, afin
qu'aucune valeur brute complete ne transite jamais vers les couches en aval.
"""

from __future__ import annotations

from src.models.detection_rgpd import CategorieRgpd


def _masquer_generique(valeur: str, visibles_debut: int = 1, visibles_fin: int = 0) -> str:
    if len(valeur) <= visibles_debut + visibles_fin:
        return "*" * max(len(valeur), 3)
    debut = valeur[:visibles_debut]
    fin = valeur[len(valeur) - visibles_fin :] if visibles_fin else ""
    return f"{debut}{'*' * max(3, len(valeur) - visibles_debut - visibles_fin)}{fin}"


def masquer_email(valeur: str) -> str:
    if "@" not in valeur:
        return _masquer_generique(valeur)
    local, domain = valeur.split("@", 1)
    premiere_lettre = local[0] if local else "*"
    domaine_parts = domain.rsplit(".", 1)
    tld = domaine_parts[-1] if len(domaine_parts) > 1 else ""
    domaine_masque = f"***.{tld}" if tld else "***"
    return f"{premiere_lettre}***@{domaine_masque}"


def masquer_identifiant_national(valeur: str) -> str:
    chiffres = "".join(c for c in valeur if c.isdigit())
    if len(chiffres) < 2:
        return "*" * max(len(valeur), 3)
    return "*" * (len(chiffres) - 2) + chiffres[-2:]


def masquer_nom(valeur: str) -> str:
    return _masquer_generique(valeur, visibles_debut=1)


def masquer_telephone(valeur: str) -> str:
    chiffres = "".join(c for c in valeur if c.isdigit())
    if len(chiffres) < 2:
        return "*" * max(len(valeur), 3)
    return "*" * (len(chiffres) - 2) + chiffres[-2:]


def masquer_mot_cle(valeur: str) -> str:
    """Masquage generique pour des categories detectees par mot-cle (sante, biometrie,
    origine/croyances) : conserve uniquement la premiere lettre."""
    return _masquer_generique(valeur, visibles_debut=1)


_MASQUEURS_PAR_CATEGORIE = {
    CategorieRgpd.CONTACT: masquer_email,
    CategorieRgpd.IDENTIFIANT_NATIONAL: masquer_identifiant_national,
    CategorieRgpd.IDENTITE: masquer_nom,
    CategorieRgpd.SANTE: masquer_mot_cle,
    CategorieRgpd.BIOMETRIE: masquer_mot_cle,
    CategorieRgpd.ORIGINE_CROYANCES: masquer_mot_cle,
}


def masquer(categorie: CategorieRgpd, valeur: str) -> str:
    """Retourne un extrait tronque/masque, jamais la valeur brute complete (FR-010a)."""
    masqueur = _MASQUEURS_PAR_CATEGORIE.get(categorie, masquer_mot_cle)
    resultat = masqueur(valeur)
    # Garde-fou : ne jamais renvoyer la valeur brute complete telle quelle.
    if resultat == valeur:
        resultat = _masquer_generique(valeur)
    return resultat
