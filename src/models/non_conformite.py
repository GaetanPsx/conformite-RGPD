"""Modele NonConformite (data-model.md ; FR-007, FR-012, FR-019)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator


class OrigineNonConformite(str, Enum):
    PROFIL_AIACT = "profil_aiact"
    DETECTION_RGPD = "detection_rgpd"


class NonConformite(BaseModel):
    description: str
    passage_source: str
    origine: OrigineNonConformite

    @field_validator("passage_source")
    @classmethod
    def _passage_source_non_vide(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "passage_source DOIT referencer un PassageLegalRecupere effectivement "
                "recupere (FR-013/FR-019) ; jamais vide/null pour une entree presente"
            )
        return v
