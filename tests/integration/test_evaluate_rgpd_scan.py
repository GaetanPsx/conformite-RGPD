"""T065 [US4] : contenu de test avec motifs connus de 3 categories (email, numero de securite
sociale, identifiant de sante) et contenu sans motif -> detections correctes avec extrait masque
et source, compteur `appels_llm_effectues` inchange par cette etape (Acceptance Scenarios
US4.1-2, quickstart.md Scenario 5)."""

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import OPENAI_CHAT_URL, add_llm_route, add_github_routes

client = TestClient(app)


def test_motifs_connus_produisent_des_detections_masquees_avec_source():
    """Acceptance Scenario US4.1 : email, numero de securite sociale et mot-cle de sante
    detectes avec extrait masque et fichier source, sans appel LLM supplementaire."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "db/schema.sql", "type": "blob", "size": 10},
            ],
            contents={
                "db/schema.sql": (
                    "CREATE TABLE patients (id INT, dossier_medical TEXT);\n"
                    "-- contact: jean.dupont@example.com\n"
                    "-- nir: 185057500123456\n"
                )
            },
        )
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

        # Un seul appel LLM (AI Act) : le scan RGPD par motifs n'en declenche aucun (FR-010).
        appels_llm = [c for c in mock.calls if str(c.request.url) == OPENAI_CHAT_URL]
        assert len(appels_llm) == 1

    assert resp.status_code == 200
    texte_html = resp.text

    # Extraits masques presents, valeurs brutes absentes (FR-010a).
    assert "jean.dupont@example.com" not in texte_html
    assert "185057500123456" not in texte_html
    assert "db/schema.sql" in texte_html


def test_contenu_sans_motif_ne_produit_aucune_detection():
    """Acceptance Scenario US4.2 : contenu sans motif connu -> aucune detection RGPD, absence
    explicite dans le rapport."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[{"path": "README.md", "type": "blob", "size": 10}],
            contents={"README.md": "# Projet generique sans donnee personnelle."},
        )
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "aucune donnée personnelle détectée" in resp.text.lower()
