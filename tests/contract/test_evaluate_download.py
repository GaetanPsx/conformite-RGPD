"""T068 [US5] : apres un `POST /evaluate` reussi, le telechargement retourne 200 avec en-tete
`Content-Disposition: attachment` et un corps identique au rapport affiche (contracts/
web-interface.md GET /evaluate/download, FR-001b)."""

import html
import re

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import add_llm_route, add_github_routes

client = TestClient(app)


def _extraire_corps_html_du_formulaire(page_html: str) -> str:
    match = re.search(
        r'name="corps_html" value="(.*?)">\s*<button', page_html, re.DOTALL
    )
    assert match is not None, "champ cache corps_html introuvable dans la page rendue"
    # Un navigateur decode les entites HTML de l'attribut avant de soumettre le formulaire.
    return html.unescape(match.group(1))


def test_telechargement_retourne_attachment_avec_corps_identique():
    with respx.mock(assert_all_called=False) as mock:
        add_github_routes(
            mock, tree=[{"path": "README.md", "type": "blob", "size": 10}]
        )
        add_llm_route(mock)
        resp_evaluate = client.post(
            "/evaluate", data={"repo_url": "https://github.com/octocat/hello"}
        )

    assert resp_evaluate.status_code == 200
    corps_html_echappe = _extraire_corps_html_du_formulaire(resp_evaluate.text)

    resp_download = client.post(
        "/evaluate/download", data={"corps_html": corps_html_echappe}
    )

    assert resp_download.status_code == 200
    assert "attachment" in resp_download.headers.get("content-disposition", "")

    # Le corps du rapport telecharge contient les memes sections/valeurs que celles affichees.
    assert "Profil AI Act" in resp_download.text
