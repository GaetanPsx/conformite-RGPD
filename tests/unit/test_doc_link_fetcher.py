"""Tests pour la recuperation d'une documentation fournie via un lien direct."""

import httpx
import pytest
import respx

from src.services.doc_link_fetcher import (
    MAX_LIEN_BYTES,
    LienDocumentationInaccessibleError,
    LienDocumentationInvalideError,
    recuperer_contenu,
)


def test_lien_valide_retourne_le_contenu():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://exemple.com/doc.txt").mock(
            return_value=httpx.Response(200, content=b"Documentation du projet.")
        )
        contenu = recuperer_contenu("https://exemple.com/doc.txt")

    assert contenu == b"Documentation du projet."


def test_lien_sans_schema_http_est_rejete():
    with pytest.raises(LienDocumentationInvalideError):
        recuperer_contenu("ftp://exemple.com/doc.txt")


def test_lien_vide_est_rejete():
    with pytest.raises(LienDocumentationInvalideError):
        recuperer_contenu("")


def test_lien_vers_hote_interne_est_rejete():
    with pytest.raises(LienDocumentationInaccessibleError):
        recuperer_contenu("http://127.0.0.1/secret")


def test_lien_vers_localhost_est_rejete():
    with pytest.raises(LienDocumentationInaccessibleError):
        recuperer_contenu("http://localhost:8000/interne")


def test_lien_avec_statut_erreur_leve_inaccessible():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://exemple.com/absent.txt").mock(return_value=httpx.Response(404))
        with pytest.raises(LienDocumentationInaccessibleError):
            recuperer_contenu("https://exemple.com/absent.txt")


def test_lien_trop_volumineux_leve_inaccessible():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://exemple.com/gros.txt").mock(
            return_value=httpx.Response(200, content=b"x" * (MAX_LIEN_BYTES + 1))
        )
        with pytest.raises(LienDocumentationInaccessibleError):
            recuperer_contenu("https://exemple.com/gros.txt")
