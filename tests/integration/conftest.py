"""Helpers partages pour les tests d'integration : mocks GitHub et Anthropic via respx.

Un seul routeur respx par test (pour eviter les conflits d'interception imbriques) : les tests
ouvrent `with respx.mock() as mock:` puis appellent `add_github_routes(mock, ...)` et/ou
`add_anthropic_route(mock, ...)` pour enregistrer les routes necessaires.
"""

from __future__ import annotations

import json
import os

import pytest
from httpx import Response

from src.services import llm_client


@pytest.fixture(autouse=True)
def _env_and_counters():
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
    # Le modele d'embedding local doit deja etre en cache (build_index.py, T016) ; force le mode
    # hors ligne pour que respx (qui mocke exclusivement GitHub/Anthropic dans ces tests) n'ait pas
    # a intercepter les requetes HTTP de huggingface_hub.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    llm_client.reset_compteurs()
    yield
    llm_client.reset_compteurs()

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

DEFAULT_CONTENTS = {
    "README.md": "# Projet\nSysteme d'aide au diagnostic medical par IA dans le secteur de la sante.",
    "requirements.txt": "torch\nscikit-learn\n",
    "src/model_inference.py": "def predict(patient_data):\n    return model(patient_data)\n",
    "db/schema.sql": (
        "CREATE TABLE patients (id INT, email VARCHAR(255), diagnostic TEXT);\n"
        "-- exemple: jean.dupont@example.com\n"
    ),
}

DEFAULT_LLM_PAYLOAD = {
    "secteur_activite": "sante",
    "finalite": "aide au diagnostic medical assistee par IA",
    "niveau_autonomie_decisionnelle": "supervisee",
    "passages_utilises": [],
}


def anthropic_response_body(payload: dict) -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "model": "claude-haiku-4-5",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def add_github_routes(
    mock,
    private: bool = False,
    tree: list | None = None,
    truncated: bool = False,
    status: int = 200,
    contents: dict | None = None,
):
    tree = tree if tree is not None else [{"path": "README.md", "type": "blob", "size": 100}]
    if status == 404:
        mock.get(url__regex=rf"{GITHUB_API_BASE}/repos/.+").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )
        return
    if status in (403, 429):
        mock.get(url__regex=rf"{GITHUB_API_BASE}/repos/.+").mock(
            return_value=Response(status, json={"message": "rate limited"})
        )
        return
    mock.get(url__regex=rf"{GITHUB_API_BASE}/repos/[^/]+/[^/]+$").mock(
        return_value=Response(200, json={"private": private, "default_branch": "main"})
    )
    mock.get(url__regex=rf"{GITHUB_API_BASE}/repos/.+/git/trees/.+").mock(
        return_value=Response(200, json={"tree": tree, "truncated": truncated})
    )

    contenu_par_chemin = {**DEFAULT_CONTENTS, **(contents or {})}
    for item in tree:
        chemin = item.get("path")
        if not chemin or item.get("type") != "blob":
            continue
        texte = contenu_par_chemin.get(chemin, f"contenu de test pour {chemin}\n")
        mock.get(url__regex=rf"{GITHUB_RAW_BASE}/.+/{chemin}$").mock(
            return_value=Response(200, text=texte)
        )


def add_anthropic_route(mock, payload: dict | None = None, status: int = 200):
    payload = payload if payload is not None else DEFAULT_LLM_PAYLOAD
    if status != 200:
        mock.post(ANTHROPIC_MESSAGES_URL).mock(return_value=Response(status, json={}))
        return
    mock.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=Response(200, json=anthropic_response_body(payload))
    )
