"""T045/T046/T047 [US2] : le rapport inclut une liste de non-conformites, chacune rattachee a un
passage legal effectivement recupere par le RAG pour cette evaluation (FR-013, FR-019,
quickstart.md Scenario 3, Acceptance Scenarios US2.1-4)."""

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)

PASSAGES_SANTE_POSSIBLES = {"RGPD-ART-6", "RGPD-ART-9"}


def test_caracteristique_de_non_conformite_connue_produit_reference_recuperee():
    """Acceptance Scenarios US2.1-2 : un depot avec une caracteristique connue de non-conformite
    (donnees de sante detectees) produit une NonConformite dont la reference correspond a un
    passage reellement retourne par le RAG pour cette evaluation."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "db/schema.sql", "type": "blob", "size": 10},
            ],
            contents={
                "db/schema.sql": (
                    "CREATE TABLE patients (id INT, diagnostic TEXT, dossier_medical TEXT);\n"
                )
            },
        )
        add_llm_route(mock)
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "non-conformité" in resp.text.lower() or "non-conformites" in resp.text.lower()
    assert any(ref in resp.text for ref in PASSAGES_SANTE_POSSIBLES)


def test_sans_caracteristique_couverte_indique_absence_explicite():
    """Acceptance Scenario US2.3 : aucune caracteristique de non-conformite couverte par le
    corpus de test -> le rapport indique explicitement l'absence de point identifie."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(mock, tree=[{"path": "README.md", "type": "blob", "size": 10}])
        add_llm_route(
            mock,
            payload={
                "secteur_activite": "generique",
                "finalite": "site vitrine",
                "niveau_autonomie_decisionnelle": "aucune",
                "passages_utilises": [],
                "non_conformites": [],
            },
        )
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "aucune non-conformité potentielle identifiée" in resp.text.lower()


def test_aspect_sans_passage_suffisamment_pertinent_ne_produit_pas_de_non_conformite_inventee():
    """Acceptance Scenario US2.4 : une categorie RGPD detectee (contact) pour laquelle aucun
    passage RAG suffisamment pertinent n'est recupere (corpus de test sans entree dediee aux
    coordonnees de contact) n'est PAS transformee en non-conformite inventee ; le rapport signale
    l'absence de reference disponible plutot qu'une citation fabriquee."""
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[{"path": "contacts.sql", "type": "blob", "size": 10}],
            contents={"contacts.sql": "INSERT INTO t VALUES ('jean.dupont@example.com');\n"},
        )
        add_llm_route(
            mock,
            payload={
                "secteur_activite": "generique",
                "finalite": "gestion de contacts",
                "niveau_autonomie_decisionnelle": "aucune",
                "passages_utilises": [],
                "non_conformites": [],
            },
        )
        resp = client.post("/evaluate", data={"repo_url": "https://github.com/octocat/hello"})

    assert resp.status_code == 200
    assert "aucune non-conformité potentielle identifiée" in resp.text.lower()
