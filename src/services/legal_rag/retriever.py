"""Recherche legale locale (RAG), sans aucun appel LLM payant (FR-018/FR-019, research.md §7).

Le corpus juridique est minuscule (une dizaine de passages) : plutot qu'embarquer un modele
d'embedding (torch + sentence-transformers, ~1 Go, plusieurs minutes de demarrage sur Azure),
la recherche est lexicale : TF-IDF (numpy) + similarite cosinus, avec normalisation francaise
(minuscules, accents retires, mots vides, racinisation par troncature). Le corpus est indexe en
memoire au premier appel (quelques millisecondes).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np

from src.models.legal_corpus import PassageLegalRecupere

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "legal_corpus" / "corpus.json"
DEFAULT_TOP_N = 8

TAILLE_MIN_MOT = 3
LONGUEUR_RACINE = 6

MOTS_VIDES = frozenset(
    """les des une aux par pour dans sur avec sans que qui quoi dont est sont ete etre ont avoir
    cette ces son ses leur leurs elle ils elles nous vous mais donc car aussi comme tout tous
    toute toutes peut peuvent doit doivent lors ainsi entre vers sous chez the and for with that
    this from are not""".split()
)

_cache: dict[str, dict] = {}


def _tokeniser(texte: str) -> list[str]:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    mots = re.findall(r"[a-z0-9]+", texte)
    return [m[:LONGUEUR_RACINE] for m in mots if len(m) >= TAILLE_MIN_MOT and m not in MOTS_VIDES]


def _vectoriser(tokens: list[str], vocabulaire: dict[str, int], idf: np.ndarray) -> np.ndarray:
    vecteur = np.zeros(len(vocabulaire), dtype=np.float32)
    for token in tokens:
        i = vocabulaire.get(token)
        if i is not None:
            vecteur[i] += 1.0
    vecteur = np.where(vecteur > 0, 1.0 + np.log(np.maximum(vecteur, 1.0)), 0.0) * idf
    norme = np.linalg.norm(vecteur)
    return vecteur / norme if norme > 0 else vecteur


def _charger_index(corpus_path: Path = CORPUS_PATH) -> dict:
    key = str(corpus_path)
    if key not in _cache:
        with open(corpus_path, encoding="utf-8") as f:
            corpus = json.load(f)
        tokens_par_passage = [
            _tokeniser(f"{e.get('theme', '')} {e['texte']}") for e in corpus
        ]
        vocabulaire = {
            mot: i for i, mot in enumerate(sorted({t for tokens in tokens_par_passage for t in tokens}))
        }
        n = len(corpus)
        df = np.zeros(len(vocabulaire), dtype=np.float32)
        for tokens in tokens_par_passage:
            for mot in set(tokens):
                df[vocabulaire[mot]] += 1.0
        idf = (np.log((1.0 + n) / (1.0 + df)) + 1.0).astype(np.float32)
        _cache[key] = {
            "vocabulaire": vocabulaire,
            "idf": idf,
            "matrice": np.stack([_vectoriser(t, vocabulaire, idf) for t in tokens_par_passage]),
            "ids": [e["id_reference"] for e in corpus],
            "textes": [e["texte"] for e in corpus],
        }
    return _cache[key]


def rechercher(
    requete: str, top_n: int = DEFAULT_TOP_N, index_path: Path = CORPUS_PATH
) -> list[PassageLegalRecupere]:
    """Retourne le top-N des passages les plus pertinents pour `requete`, tries par score
    de pertinence decroissant. 0 appel LLM payant : calcul local uniquement."""
    if not requete or not requete.strip():
        return []

    index = _charger_index(index_path)
    vecteur = _vectoriser(_tokeniser(requete), index["vocabulaire"], index["idf"])
    scores = index["matrice"] @ vecteur

    ordre = np.argsort(-scores)[:top_n]
    return [
        PassageLegalRecupere(
            id_reference=index["ids"][i], texte=index["textes"][i], score_pertinence=float(scores[i])
        )
        for i in ordre
    ]
