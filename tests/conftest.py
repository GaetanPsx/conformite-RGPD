"""Fixtures partagees pour l'ensemble de la suite de tests (contract, integration, unit) :
variables d'environnement requises par le pipeline complet et reinitialisation de l'etat
module-level (compteurs LLM, rate limiting) entre chaque test, afin qu'un test n'affecte pas
le suivant quel que soit son repertoire.
"""

from __future__ import annotations

import os

import pytest

from src.services import llm_client
from src.web import app as app_module


@pytest.fixture(autouse=True)
def _env_and_counters():
    os.environ.setdefault("MISTRAL_API_KEY", "test-key-not-real")
    # Le modele d'embedding local doit deja etre en cache (build_index.py, T016) ; force le mode
    # hors ligne pour que respx (qui mocke exclusivement GitHub/Anthropic dans ces tests) n'ait pas
    # a intercepter les requetes HTTP de huggingface_hub.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    llm_client.reset_compteurs()
    # Le rate limiting en memoire de app.py (etat module-level) doit etre reinitialise entre
    # chaque test, sans quoi l'accumulation de requetes sur l'ensemble de la suite declenche de
    # faux 429 sans rapport avec le scenario teste.
    app_module._historique_requetes.clear()
    yield
    llm_client.reset_compteurs()
    app_module._historique_requetes.clear()
