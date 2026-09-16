"""Modeles SelectionAiAct et SelectionRgpd (data-model.md ; FR-006, FR-006a).

Contrainte : en mode depot, `fichiers` DOIT contenir au maximum 15 elements par selection
(SelectionAiAct et SelectionRgpd sont bornees independamment). En mode documentation, `fichiers`
contient un seul element synthetique representant la DocumentationFournie.
"""

from __future__ import annotations

from pydantic import BaseModel

from src.models.fichier import FichierAvecContenu

MAX_FICHIERS_PAR_CATEGORIE = 15


class SelectionAiAct(BaseModel):
    fichiers: list[FichierAvecContenu]
    selection_partielle: bool = False
    taille_totale_caracteres: int = 0


class SelectionRgpd(BaseModel):
    fichiers: list[FichierAvecContenu]
    selection_partielle: bool = False
