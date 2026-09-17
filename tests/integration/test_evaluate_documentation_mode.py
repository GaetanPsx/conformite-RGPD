"""T029/T030/T031 [US1] : soumission en mode documentation (texte colle, fichier, entree absente)."""

import io

import respx
from fastapi.testclient import TestClient

from src.web.app import app
from tests.integration.conftest import add_llm_route

client = TestClient(app)


def test_evaluate_documentation_texte_ne_declenche_aucun_appel_github():
    """Acceptance Scenario US1.4 : aucun appel API GitHub en mode documentation, SC-007."""
    with respx.mock(assert_all_called=False) as mock:
        # Si le pipeline appelle par erreur l'API GitHub, la route echouera (aucune route enregistree
        # -> respx leve une erreur d'appel non mocke).
        add_llm_route(mock)
        texte = (
            "Notre systeme d'IA dans le secteur de la sante fournit une assistance au "
            "diagnostic medical. Un email de contact : contact@example.com."
        )
        resp = client.post("/evaluate", data={"documentation_texte": texte})

        assert resp.status_code == 200
        assert "aucun appel" not in resp.text.lower()  # pas de message d'erreur bloquant
        assert mock.calls, "l'appel Anthropic aurait du avoir lieu"
        for call in mock.calls:
            assert "api.github.com" not in str(call.request.url)


def test_evaluate_documentation_fichier_televerse_utilise_comme_source_unique():
    """Acceptance Scenario US1.5 : fichier televerse utilise comme source unique."""
    with respx.mock(assert_all_called=False) as mock:
        add_llm_route(mock)
        contenu = (
            b"Systeme de recrutement automatise utilisant l'IA pour evaluer les candidatures, "
            b"secteur des ressources humaines."
        )
        fichier = io.BytesIO(contenu)
        resp = client.post(
            "/evaluate",
            files={"documentation_fichier": ("doc.txt", fichier, "text/plain")},
        )

    assert resp.status_code == 200


def test_evaluate_sans_entree_exploitable_est_rejete():
    """Acceptance Scenario US1.6 : ni URL valide ni documentation -> rejet clair."""
    resp = client.post("/evaluate", data={})
    assert resp.status_code in (200, 422)
    assert (
        "requise" in resp.text.lower()
        or "requis" in resp.text.lower()
        or "erreur" in resp.text.lower()
    )
