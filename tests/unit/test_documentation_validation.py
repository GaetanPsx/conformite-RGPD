"""T075 [Phase 8] : un fichier de documentation televerse non-texte (binaire) est rejete avant tout
appel LLM (Edge Cases, FR-016).

La validation vit dans la route `POST /evaluate` (decodage UTF-8 du contenu televerse, src/web/
app.py) plutot que dans un module dedie : le test exerce ce comportement via le client de test,
sans enregistrer de route respx pour Anthropic/GitHub, afin qu'un appel HTTP non attendu fasse
echouer le test.
"""

import respx
from fastapi.testclient import TestClient

from src.services import llm_client
from src.web.app import app

client = TestClient(app)


def test_fichier_binaire_rejete_sans_appel_llm():
    contenu_binaire = bytes(range(256))

    with respx.mock(assert_all_called=False):
        resp = client.post(
            "/evaluate",
            files={"documentation_fichier": ("dump.bin", contenu_binaire, "application/octet-stream")},
        )

    assert resp.status_code == 422
    assert "binaire" in resp.text.lower() or "exploitable" in resp.text.lower()
    assert llm_client.appels_llm_effectues == 0


def test_fichier_texte_valide_non_rejete_pour_ce_motif():
    with respx.mock(assert_all_called=False) as mock:
        from tests.integration.conftest import add_llm_route

        add_llm_route(mock)
        resp = client.post(
            "/evaluate",
            files={
                "documentation_fichier": (
                    "notes.txt",
                    b"Documentation textuelle valide.",
                    "text/plain",
                )
            },
        )

    assert resp.status_code == 200
