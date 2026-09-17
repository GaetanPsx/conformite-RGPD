"""T026/T027/T028 [US1] : soumission en mode depot (GitHub + LLM mockes via respx)."""

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)


def test_evaluate_repo_mode_produit_profil_avec_citation():
    """Acceptance Scenario US1.1 : secteur/finalite/autonomie chacun avec >=1 citation."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 100},
                {"path": "requirements.txt", "type": "blob", "size": 50},
                {"path": "src/model_inference.py", "type": "blob", "size": 200},
            ],
        )
        add_llm_route(
            mock,
            payload={
                "secteur_activite": "sante",
                "finalite": "diagnostic assiste par IA",
                "niveau_autonomie_decisionnelle": "supervisee",
                "passages_utilises": ["AIACT-ANNEXE-III"],
            },
        )
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "sante" in resp.text
    assert "diagnostic assiste par IA" in resp.text
    assert "supervisee" in resp.text
    # Au moins une citation legale (parmi celles effectivement recuperees par le RAG, FR-019) :
    # seule une reference effectivement retournee par le retriever pour cette evaluation peut
    # etre citee (invariant FR-013/FR-019).
    assert "AIACT-ANNEXE-III" in resp.text


def test_evaluate_repo_mode_detecte_categories_rgpd_avec_source():
    """Acceptance Scenario US1.2 : detections RGPD avec fichier source."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "db/schema.sql", "type": "blob", "size": 10},
            ],
        )
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "db/schema.sql" in resp.text or "contact" in resp.text


def test_evaluate_repo_mode_sans_fichier_pertinent_indique_absence():
    """Acceptance Scenario US1.3 : aucun fichier pertinent -> absence explicite."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(mock, tree=[])
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "aucune donnée personnelle détectée" in resp.text.lower() or "aucun élément" in resp.text.lower()
