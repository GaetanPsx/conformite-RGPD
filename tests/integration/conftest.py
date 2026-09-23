"""Helpers partages pour les tests d'integration : mocks GitHub et Mistral AI via respx.

Un seul routeur respx par test (pour eviter les conflits d'interception imbriques) : les tests
ouvrent `with respx.mock() as mock:` puis appellent `add_github_routes(mock, ...)` et/ou
`add_llm_route(mock, ...)` pour enregistrer les routes necessaires.

Les fixtures autouse (variables d'environnement, reinitialisation des compteurs/rate limiting)
sont definies dans `tests/conftest.py` (partagees par toute la suite, y compris les tests
contract qui exercent aussi le pipeline complet).
"""

from __future__ import annotations

import json

from httpx import Response

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

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


def mistral_response_body(payload: dict) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "mistral-small-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(payload)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
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


def add_llm_route(mock, payload: dict | None = None, status: int = 200):
    payload = payload if payload is not None else DEFAULT_LLM_PAYLOAD
    if status != 200:
        mock.post(MISTRAL_CHAT_URL).mock(return_value=Response(status, json={}))
        return
    mock.post(MISTRAL_CHAT_URL).mock(
        return_value=Response(200, json=mistral_response_body(payload))
    )
