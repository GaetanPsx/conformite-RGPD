"""Determination du mode d'entree (depot vs documentation) (FR-001, research.md §8)."""

from __future__ import annotations

from src.models.depot import Mode, ModeEntree, parse_github_url


class AucuneEntreeExploitableError(Exception):
    """Ni URL de depot valide, ni documentation fournie (FR-001, Edge Cases)."""


def determiner_mode(
    repo_url: str | None,
    documentation_texte: str | None = None,
    documentation_fichier: bytes | None = None,
) -> ModeEntree:
    """Regle deterministe (research.md §8) :

    - URL GitHub valide dans `repo_url` -> mode depot (documentation fournie en parallele,
      si non vide, est ignoree et signalee via `source_ignoree=true`).
    - Sinon, `documentation_texte` non vide ou `documentation_fichier` non vide -> mode
      documentation.
    - Sinon -> AucuneEntreeExploitableError.
    """
    url_valide = bool(repo_url) and parse_github_url(repo_url) is not None
    documentation_fournie = bool(documentation_texte and documentation_texte.strip()) or bool(
        documentation_fichier
    )

    if url_valide:
        return ModeEntree(mode=Mode.DEPOT, source_ignoree=documentation_fournie)

    if documentation_fournie:
        return ModeEntree(mode=Mode.DOCUMENTATION, source_ignoree=False)

    raise AucuneEntreeExploitableError(
        "Une URL de depot GitHub valide ou une documentation (texte/fichier) est requise (FR-001)"
    )
