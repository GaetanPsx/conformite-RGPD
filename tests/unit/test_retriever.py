"""T025 [US1] : cas conforme + cas non conforme pour la recuperation RAG sur l'index de test
figue (FR-018/FR-019)."""

from src.services.legal_rag.retriever import rechercher


def test_requete_pertinente_retourne_passages_ancres():
    resultats = rechercher(
        "traitement de donnees de sante d'un patient sans base legale explicite mentionnee"
    )
    assert len(resultats) > 0
    ids = [r.id_reference for r in resultats]
    assert "RGPD-ART-9" in ids
    assert all(r.score_pertinence > 0 for r in resultats)


def test_requete_hors_sujet_retourne_scores_bas_ou_liste_vide():
    resultats_pertinents = rechercher("systeme de credit scoring automatise haut risque")
    resultats_hors_sujet = rechercher("xyzzy plugh qwerty asdf zzzzz nonsense gibberish")
    meilleur_score_pertinent = max(r.score_pertinence for r in resultats_pertinents)
    meilleur_score_hors_sujet = max(r.score_pertinence for r in resultats_hors_sujet)
    assert meilleur_score_hors_sujet < meilleur_score_pertinent


def test_requete_vide_retourne_liste_vide():
    assert rechercher("") == []
