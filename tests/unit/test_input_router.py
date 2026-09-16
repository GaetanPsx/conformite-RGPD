"""T022 [US1] : cas conforme + cas non conforme pour determiner_mode (FR-001)."""

import pytest

from src.models.depot import Mode
from src.services.input_router import AucuneEntreeExploitableError, determiner_mode


def test_url_github_valide_seule_donne_mode_depot():
    resultat = determiner_mode(repo_url="https://github.com/octocat/hello-world")
    assert resultat.mode == Mode.DEPOT
    assert resultat.source_ignoree is False


def test_documentation_seule_donne_mode_documentation():
    resultat = determiner_mode(repo_url=None, documentation_texte="Un texte de documentation.")
    assert resultat.mode == Mode.DOCUMENTATION
    assert resultat.source_ignoree is False


def test_documentation_fichier_seul_donne_mode_documentation():
    resultat = determiner_mode(
        repo_url=None, documentation_texte=None, documentation_fichier=b"contenu du fichier"
    )
    assert resultat.mode == Mode.DOCUMENTATION


def test_url_et_documentation_fournies_ensemble_privilegie_mode_depot():
    resultat = determiner_mode(
        repo_url="https://github.com/octocat/hello-world",
        documentation_texte="Documentation ignoree",
    )
    assert resultat.mode == Mode.DEPOT
    assert resultat.source_ignoree is True


def test_ni_url_ni_documentation_leve_erreur():
    with pytest.raises(AucuneEntreeExploitableError):
        determiner_mode(repo_url=None, documentation_texte=None, documentation_fichier=None)


def test_url_invalide_sans_documentation_leve_erreur():
    with pytest.raises(AucuneEntreeExploitableError):
        determiner_mode(repo_url="https://example.com/not-github", documentation_texte="   ")
