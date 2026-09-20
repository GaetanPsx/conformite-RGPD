"""Modele DocumentationFournie (data-model.md ; FR-001, FR-006a, FR-016)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator


class SourceDocumentation(str, Enum):
    TEXTE_COLLE = "texte_colle"
    FICHIER_TELEVERSE = "fichier_televerse"
    LIEN_URL = "lien_url"


class DocumentationFournie(BaseModel):
    """Documentation de projet soumise directement par l'utilisateur (mode documentation)."""

    source: SourceDocumentation
    contenu: str
    nom_fichier: str | None = None
    tronque: bool = False

    @field_validator("contenu")
    @classmethod
    def _contenu_non_vide(cls, v: str) -> str:
        if v is None or v.strip() == "":
            raise ValueError("contenu DOIT etre non vide et exploitable comme texte (FR-016)")
        return v
