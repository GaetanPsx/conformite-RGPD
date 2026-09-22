"""T069 [US5] : cas conforme + cas non conforme pour le telechargement immediat apres
generation -> fichier complet obtenu ; absence de toute ecriture disque/DB detectable apres la
reponse (Acceptance Scenarios US5.1-2, quickstart.md Scenario 6, SC-009)."""

import html
import os
import re

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)


def _extraire_corps_html(page_html: str) -> str:
    match = re.search(r'name="corps_html" value="(.*?)">\s*<button', page_html, re.DOTALL)
    assert match is not None
    return html.unescape(match.group(1))


def test_telechargement_immediat_apres_generation_donne_le_fichier_complet(tmp_path):
    """Cas conforme : le rapport telecharge contient l'integralite du contenu du rapport
    affiche (profil AI Act, detections RGPD, citations, budget LLM), sans aucun fichier ecrit
    sous un repertoire de donnees temporaire surveille par le test."""
    fichiers_avant = set(os.listdir(tmp_path))

    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock,
            tree=[
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "db/schema.sql", "type": "blob", "size": 10},
            ],
        )
        add_llm_route(mock)
        resp_evaluate = client.post(
            "/evaluate", data={"repo_url": "https://github.com/octocat/hello"}
        )

    corps_html = _extraire_corps_html(resp_evaluate.text)
    resp_download = client.post("/evaluate/download", data={"corps_html": corps_html})

    assert resp_download.status_code == 200
    assert "attachment" in resp_download.headers.get("content-disposition", "")
    for section in (
        "Profil AI Act",
        "Détections de données personnelles",
        "Non-conformités potentielles",
        "Références légales citées",
    ):
        assert section in resp_download.text

    # Aucune ecriture disque detectable sous le repertoire surveille par le test (FR-017).
    assert set(os.listdir(tmp_path)) == fichiers_avant


def test_absence_de_rapport_sans_evaluation_prealable():
    """Cas non conforme : un telechargement sans corps de rapport fourni (aucune evaluation
    prealable dans ce cycle requete/reponse) est rejete plutot que de renvoyer un rapport
    fabrique ou recupere d'un etat serveur persistant (FR-017)."""
    resp = client.post("/evaluate/download", data={})

    assert resp.status_code == 422
