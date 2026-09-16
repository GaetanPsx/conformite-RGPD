"""Modele ProfilAiAct (data-model.md ; FR-007, FR-014).

Important (FR-014) : ce modele ne DOIT JAMAIS porter de champ de score ou de niveau de risque de
conformite agrege. `niveau_autonomie_decisionnelle` est une observation descriptive fermee a 4
valeurs (FR-007a), jamais un verdict de risque.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class NiveauAutonomieDecisionnelle(str, Enum):
    AUCUNE = "aucune"
    ASSISTEE = "assistee"
    SUPERVISEE = "supervisee"
    AUTONOME = "autonome"


class ProfilAiAct(BaseModel):
    secteur_activite: str | None = None
    finalite: str | None = None
    niveau_autonomie_decisionnelle: NiveauAutonomieDecisionnelle | None = None
    fichiers_source: list[str] = []
    passages_utilises: list[str] = []
    echec: bool = False
