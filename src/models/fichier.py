"""Modeles FichierDepot et FichierAvecContenu (data-model.md ; FR-003)."""

from __future__ import annotations

from pydantic import BaseModel

from src.models.documentation import DocumentationFournie


class FichierDepot(BaseModel):
    """Un chemin de fichier liste dans le depot, sans contenu telecharge (FR-003)."""

    chemin: str
    taille_octets: int | None = None
    extension: str | None = None
    profondeur: int = 0

    @staticmethod
    def depuis_chemin(chemin: str, taille_octets: int | None = None) -> "FichierDepot":
        chemin_norm = chemin.lstrip("/")
        extension = None
        if "." in chemin_norm.rsplit("/", 1)[-1]:
            extension = "." + chemin_norm.rsplit(".", 1)[-1]
        profondeur = chemin_norm.count("/")
        return FichierDepot(
            chemin=chemin_norm,
            taille_octets=taille_octets,
            extension=extension,
            profondeur=profondeur,
        )


class FichierAvecContenu(BaseModel):
    """Fichier (ou documentation) avec son contenu retenu pour une selection (type partage)."""

    fichier: FichierDepot | DocumentationFournie
    contenu: str
    tronque: bool = False
