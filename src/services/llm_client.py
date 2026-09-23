"""Client LLM encapsulant l'unique appel a l'API OpenAI (FR-007, FR-008, FR-009, FR-016).

Modele gpt-4.1-nano, temperature 0 pour la reproductibilite (research.md §3). `appeler_llm` ne
leve jamais d'exception non geree : en cas d'echec (reponse vide/malformee/non-JSON, erreur
reseau, quota), elle journalise la cause et retourne None plutot que de faire planter le
pipeline (Edge Cases).

Budget de tokens (programme "data sharing" OpenAI, usage tiers 1-2 : 2 500 000 tokens/jour
gratuits partages par les modeles mini/nano) :
  - cible : ~50 evaluations/jour  ->  2 500 000 / 50 = 50 000 tokens par evaluation ;
  - une evaluation = au plus 2 appels LLM (FR-009)  ->  25 000 tokens par appel ;
  - sortie plafonnee a MAX_TOKENS_SORTIE (le JSON attendu est court) ;
  - entree plafonnee a MAX_PROMPT_CHARS = 40 000 caracteres, soit ~10 000 tokens a 4 car./token
    et au pire ~20 000 a 2 car./token (code/texte dense).
Pire cas par evaluation : 2 x (20 000 + 2 048) ~ 44 100 tokens < 50 000, donc ~56 evaluations/jour.
gpt-4.1-nano n'est pas un modele a raisonnement : aucun token de reflexion cache n'est facture.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-4.1-nano-2025-04-14"
MAX_PROMPT_CHARS = 40_000
MAX_TOKENS_SORTIE = 2048

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
    """Appelle le LLM (OpenAI, gpt-4.1-nano, temperature 0) et parse la reponse JSON.

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

            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""), max_retries=2)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS_SORTIE,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        if not response.choices:
            logger.error("LLM: reponse sans choices")
            return None
        texte = response.choices[0].message.content or ""
        if not texte.strip():
            logger.error("LLM: contenu vide (finish_reason=%s)", response.choices[0].finish_reason)
            return None
        resultat = _extraire_json(texte)
        if resultat is None:
            logger.error("LLM: reponse non-JSON : %s", texte[:500])
        return resultat
    except Exception:
        logger.exception("LLM: appel OpenAI en echec")
        return None
