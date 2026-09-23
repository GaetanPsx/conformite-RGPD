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
    os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
    llm_client.reset_compteurs()
    # Le rate limiting en memoire de app.py (etat module-level) doit etre reinitialise entre
    # chaque test, sans quoi l'accumulation de requetes sur l'ensemble de la suite declenche de
    # faux 429 sans rapport avec le scenario teste.
    app_module._historique_requetes.clear()
    yield
    llm_client.reset_compteurs()
    app_module._historique_requetes.clear()
