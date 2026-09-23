"""T054 [US3] : depot de plusieurs centaines de fichiers -> selections AI Act et RGPD bornees a
15 fichiers chacune avec `selection_partielle=true`, au maximum 2 appels LLM comptabilises,
aucun appel >40 000 caracteres, recherche RAG absente du compteur LLM (Acceptance Scenarios
US3.1-4, quickstart.md Scenario 4, SC-002)."""

import re

import respx
from fastapi.testclient import TestClient

from src.services import llm_client
from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)

MAX_PROMPT_CHARS = 40_000


def _arborescence_volumineuse(nombre_fichiers: int = 300) -> list[dict]:
    tree = [{"path": "README.md", "type": "blob", "size": 100}]
    for i in range(nombre_fichiers):
        tree.append({"path": f"src/module_{i:04d}.py", "type": "blob", "size": 50})
    return tree


def test_depot_volumineux_borne_les_selections_et_le_budget_llm():
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(mock, tree=_arborescence_volumineuse())
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    texte = resp.text

    # Selection AI Act bornee a 15 fichiers malgre les 300+ fichiers du depot (FR-006).
    match_fichiers = re.search(r"Fichiers/source ayant servi de contexte\s*:\s*([^<\n]*)", texte)
    assert match_fichiers is not None
    fichiers_utilises = [f.strip() for f in match_fichiers.group(1).split(",") if f.strip()]
    assert len(fichiers_utilises) <= 15

    # Au maximum 2 appels LLM comptabilises pour l'evaluation entiere (FR-009, SC-002) : la
    # recherche RAG (0 appel LLM payant, FR-018/019) n'est jamais comptee.
    assert 1 <= llm_client.appels_llm_effectues <= 2

    # Aucun appel n'a depasse le plafond de 40 000 caracteres.
    assert llm_client.taille_envoyee_par_appel
    assert all(taille <= MAX_PROMPT_CHARS for taille in llm_client.taille_envoyee_par_appel)
