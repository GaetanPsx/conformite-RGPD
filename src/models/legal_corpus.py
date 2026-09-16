"""PassageLegalRecupere et CorpusJuridique (data-model.md ; FR-013, FR-018, FR-019)."""

from __future__ import annotations

from pydantic import BaseModel


class CorpusJuridique(BaseModel):
    """Entree statique en lecture seule du corpus juridique de reference."""

    id_reference: str
    texte: str | None = None
    theme: str
    embedding: list[float] | None = None


class PassageLegalRecupere(BaseModel):
    """Passage effectivement retourne par le composant RAG pour une evaluation (FR-018/019)."""

    id_reference: str
    texte: str
    score_pertinence: float
