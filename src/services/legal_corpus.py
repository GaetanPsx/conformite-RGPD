"""Acces en lecture seule au corpus juridique de reference (FR-013)."""

from __future__ import annotations

import json
from pathlib import Path

from src.models.legal_corpus import CorpusJuridique

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "legal_corpus" / "corpus.json"


def charger_corpus(corpus_path: Path = CORPUS_PATH) -> list[CorpusJuridique]:
    with open(corpus_path, encoding="utf-8") as f:
        data = json.load(f)
    return [CorpusJuridique(**entry) for entry in data]
