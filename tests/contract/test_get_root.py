"""T032 [US1] : GET / retourne 200 avec le formulaire (contracts/web-interface.md GET /)."""

from fastapi.testclient import TestClient

from src.web.app import app


def test_get_root_retourne_formulaire():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'name="repo_url"' in resp.text
    assert 'name="documentation_texte"' in resp.text
    assert 'name="documentation_fichier"' in resp.text
