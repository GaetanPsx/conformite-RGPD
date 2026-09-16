"""Script hors ligne : encode le corpus juridique et ecrit l'index vectoriel versionne (FR-018).

Ne jamais executer ce script a l'execution d'une evaluation : il s'agit d'une etape hors ligne,
executee une seule fois (research.md §7), dont le resultat (`index.npz`) est committe.

Usage: python -m src.services.legal_rag.build_index
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "legal_corpus" / "corpus.json"
INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "legal_corpus" / "index.npz"


def charger_corpus_brut(corpus_path: Path = CORPUS_PATH) -> list[dict]:
    with open(corpus_path, encoding="utf-8") as f:
        return json.load(f)


def construire_index(
    corpus_path: Path = CORPUS_PATH, index_path: Path = INDEX_PATH, model_name: str = MODEL_NAME
) -> None:
    from sentence_transformers import SentenceTransformer

    corpus = charger_corpus_brut(corpus_path)
    textes = [entry["texte"] for entry in corpus]
    ids = [entry["id_reference"] for entry in corpus]
    themes = [entry.get("theme", "") for entry in corpus]

    model = SentenceTransformer(model_name)
    embeddings = model.encode(textes, normalize_embeddings=True, convert_to_numpy=True)

    index_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        index_path,
        embeddings=embeddings.astype(np.float32),
        ids=np.array(ids, dtype=object),
        textes=np.array(textes, dtype=object),
        themes=np.array(themes, dtype=object),
        model_name=np.array(model_name),
    )
    print(f"Index ecrit dans {index_path} ({len(ids)} passages, modele={model_name})")


if __name__ == "__main__":
    construire_index()
