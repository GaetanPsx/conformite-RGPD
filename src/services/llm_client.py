"""Client LLM encapsulant l'unique appel a l'API OpenAI (FR-007, FR-008, FR-009, FR-016).

Modele gpt-4o-mini, temperature 0 pour la reproductibilite (research.md §3). `appeler_llm` ne leve
jamais d'exception non geree : en cas d'echec (reponse vide/malformee/non-JSON, erreur reseau),
elle retourne None plutot que de faire planter le pipeline (Edge Cases).
"""

from __future__ import annotations

import json
import os

MODEL_NAME = "gpt-4o-mini"
MAX_PROMPT_CHARS = 40_000

# Compteurs de budget exposes pour le suivi (FR-015), reinitialisables par evaluation via reset().
appels_llm_effectues = 0
taille_envoyee_par_appel: list[int] = []


def reset_compteurs() -> None:
    global appels_llm_effectues, taille_envoyee_par_appel
    appels_llm_effectues = 0
    taille_envoyee_par_appel = []


def _extraire_json(texte: str) -> dict | None:
    texte = texte.strip()
    try:
        return json.loads(texte)
    except (json.JSONDecodeError, TypeError):
        pass
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut != -1 and fin != -1 and fin > debut:
        try:
            return json.loads(texte[debut : fin + 1])
        except json.JSONDecodeError:
            return None
    return None


def appeler_llm(prompt: str, client=None) -> dict | None:
    """Appelle le LLM (OpenAI, gpt-4o-mini, temperature 0) et parse la reponse JSON.

    Retourne None si l'appel echoue ou si la reponse n'est pas un JSON exploitable.
    Incremente les compteurs de budget (appels_llm_effectues, taille_envoyee_par_appel)
    quel que soit le resultat de l'appel (un appel tente compte, FR-009/FR-015).
    """
    global appels_llm_effectues, taille_envoyee_par_appel

    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS]

    appels_llm_effectues += 1
    taille_envoyee_par_appel.append(len(prompt))

    try:
        if client is None:
            import openai

            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        if not response.choices:
            return None
        texte = response.choices[0].message.content or ""
        if not texte.strip():
            return None
        return _extraire_json(texte)
    except Exception:
        return None
