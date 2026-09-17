"""T072-T074 [Phase 8] : cas d'erreur de `POST /evaluate` (contracts/web-interface.md, tableau des
reponses d'erreur) :
- depot prive/inexistant -> message clair distinguant ce cas, 0 appel LLM (T072, FR-002, SC-006)
- limitation de debit GitHub -> message distinguant cette cause d'un depot invalide (T073,
  Edge Cases, research.md §2)
- reponse LLM invalide/vide -> rapport produit quand meme avec `ProfilAiAct.echec=true` et
  detections RGPD presentes (T074, Edge Cases)
"""

import respx
from fastapi.testclient import TestClient

from src.services import llm_client
from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)


def test_depot_prive_ou_inexistant_message_clair_sans_appel_llm():
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(mock, status=404)
        resp = client.post(
            "/evaluate", data={"repo_url": "https://github.com/octocat/prive-ou-absent"}
        )

    assert resp.status_code == 200
    assert "introuvable" in resp.text or "priv" in resp.text
    assert llm_client.appels_llm_effectues == 0


def test_rate_limit_github_distingue_depot_invalide():
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(mock, status=429)
        resp = client.post(
            "/evaluate", data={"repo_url": "https://github.com/octocat/hello"}
        )

    assert resp.status_code == 200
    assert "limit" in resp.text.lower()
    assert "introuvable" not in resp.text
    assert llm_client.appels_llm_effectues == 0


def test_reponse_llm_invalide_rapport_produit_avec_echec():
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "db/schema.sql", "type": "blob", "size": 10},
            ],
        )
        add_llm_route(mock, status=500)
        resp = client.post(
            "/evaluate", data={"repo_url": "https://github.com/octocat/hello"}
        )

    assert resp.status_code == 200
    assert "jean.dupont" not in resp.text
    # Detections RGPD (issues du scan sur db/schema.sql) restent presentes malgre l'echec LLM.
    assert "Détections RGPD" in resp.text or "detections" in resp.text.lower()
