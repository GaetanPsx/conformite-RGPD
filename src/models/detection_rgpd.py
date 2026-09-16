"""Modele DetectionRgpd (data-model.md ; FR-010, FR-010a)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class CategorieRgpd(str, Enum):
    IDENTITE = "identite"
    CONTACT = "contact"
    IDENTIFIANT_NATIONAL = "identifiant_national"
    SANTE = "sante"
    BIOMETRIE = "biometrie"
    ORIGINE_CROYANCES = "origine_croyances"


class DetectionRgpd(BaseModel):
    categorie: CategorieRgpd
    source: str
    motif: str
    extrait_masque: str
