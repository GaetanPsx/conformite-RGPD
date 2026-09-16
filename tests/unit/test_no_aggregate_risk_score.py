"""T032a [US1] : aucun champ de score/niveau de risque agrege sur ProfilAiAct,
ProfilProjetCombine, RapportFinal, ni dans le HTML rendu (FR-014)."""

from src.models.profil_aiact import ProfilAiAct
from src.models.rapport import ProfilProjetCombine, RapportFinal

RISK_KEYWORDS = ["score", "risque_global", "risk_score", "niveau_risque", "risque_agrege"]


def _noms_champs(model_cls) -> list[str]:
    return list(model_cls.model_fields.keys())


def test_profil_aiact_sans_champ_de_risque():
    champs = _noms_champs(ProfilAiAct)
    for champ in champs:
        for kw in RISK_KEYWORDS:
            assert kw not in champ.lower(), f"champ suspect: {champ}"


def test_profil_projet_combine_sans_champ_de_risque():
    champs = _noms_champs(ProfilProjetCombine)
    for champ in champs:
        for kw in RISK_KEYWORDS:
            assert kw not in champ.lower(), f"champ suspect: {champ}"


def test_rapport_final_sans_champ_de_risque():
    champs = _noms_champs(RapportFinal)
    for champ in champs:
        for kw in RISK_KEYWORDS:
            assert kw not in champ.lower(), f"champ suspect: {champ}"


def test_html_rendu_sans_mention_de_score_agrege():
    from src.services.report_builder import rendre_html
    from src.models.depot import Mode, ModeEntree

    profil = ProfilProjetCombine(
        mode_entree=ModeEntree(mode=Mode.DOCUMENTATION),
        profil_aiact=ProfilAiAct(),
        appels_llm_effectues=0,
        taille_envoyee_par_appel=[],
    )
    rapport = rendre_html(profil)
    html_lower = rapport.html.lower()
    for kw in ["risque global", "score de conformite", "niveau de risque global", "risk_score"]:
        assert kw not in html_lower
