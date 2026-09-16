"""Recherche legale locale (RAG), sans aucun appel LLM payant (FR-018/FR-019, research.md §7).

Charge l'index vectoriel pre-calcule (`index.npz`), encode la requete avec le meme modele
d'embedding local, et calcule une similarite cosinus (numpy) pour retourner le top-N des passages
les plus pertinents.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.models.legal_corpus import PassageLegalRecupere

INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "legal_corpus" / "index.npz"
DEFAULT_TOP_N = 8

_cache: dict[str, object] = {}


def _charger_index(index_path: Path = INDEX_PATH):
    key = str(index_path)
    if key not in _cache:
        data = np.load(index_path, allow_pickle=True)
        _cache[key] = {
            "embeddings": data["embeddings"],
            "ids": data["ids"],
            "textes": data["textes"],
            "themes": data["themes"],
            "model_name": str(data["model_name"]),
        }
    return _cache[key]


_model_cache: dict[str, object] = {}


def _charger_modele(model_name: str):
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer

        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def rechercher(
    requete: str, top_n: int = DEFAULT_TOP_N, index_path: Path = INDEX_PATH
) -> list[PassageLegalRecupere]:
    """Retourne le top-N des passages les plus pertinents pour `requete`, tries par score
    de pertinence decroissant. 0 appel LLM payant : encodage local uniquement."""
    if not requete or not requete.strip():
        return []

    index = _charger_index(index_path)
    model = _charger_modele(index["model_name"])

    vecteur_requete = model.encode([requete], normalize_embeddings=True, convert_to_numpy=True)[0]
    embeddings = index["embeddings"]
    scores = embeddings @ vecteur_requete  # cosine similarity (vecteurs deja normalises)

    ordre = np.argsort(-scores)[:top_n]
    resultats = []
    for i in ordre:
        resultats.append(
            PassageLegalRecupere(
                id_reference=str(index["ids"][i]),
                texte=str(index["textes"][i]),
                score_pertinence=float(scores[i]),
            )
        )
    return resultats
