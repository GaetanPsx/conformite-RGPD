"""T044 [US2] : cas conforme + cas non conforme pour la production de NonConformite a partir de
la reponse LLM (ProfilAiAct) et de la liste de PassageLegalRecupere effectivement recuperes
(FR-013, FR-019, data-model.md NonConformite invariant)."""

from src.models.documentation import DocumentationFournie, SourceDocumentation
from src.models.fichier import FichierAvecContenu
from src.models.legal_corpus import PassageLegalRecupere
from src.models.selection import SelectionAiAct
from src.services import aiact_analyzer


def _selection() -> SelectionAiAct:
    doc = DocumentationFournie(
        source=SourceDocumentation.TEXTE_COLLE,
        contenu="Systeme d'aide au diagnostic medical par IA dans le secteur de la sante.",
    )
    fc = FichierAvecContenu(fichier=doc, contenu=doc.contenu, tronque=False)
    return SelectionAiAct(fichiers=[fc], selection_partielle=False, taille_totale_caracteres=0)


PASSAGES = [
    PassageLegalRecupere(
        id_reference="RGPD-ART-9", texte="texte article 9", score_pertinence=0.9
    ),
]


def test_aspect_avec_passage_pertinent_produit_non_conformite(monkeypatch):
    """Cas conforme : le LLM rattache une non-conformite a un passage effectivement transmis ->
    la NonConformite produite reference ce passage."""

    def _appel_mocke(prompt, client=None):
        return {
            "secteur_activite": "sante",
            "finalite": "diagnostic assiste",
            "niveau_autonomie_decisionnelle": "supervisee",
            "passages_utilises": ["RGPD-ART-9"],
            "non_conformites": [
                {
                    "description": "Absence de base legale explicite pour les donnees de sante.",
                    "passage_source": "RGPD-ART-9",
                }
            ],
        }

    monkeypatch.setattr(aiact_analyzer.llm_client, "appeler_llm", _appel_mocke)

    profil, non_conformites = aiact_analyzer.analyser(_selection(), PASSAGES)

    assert profil.echec is False
    assert len(non_conformites) == 1
    assert non_conformites[0].passage_source == "RGPD-ART-9"
    assert non_conformites[0].origine.value == "profil_aiact"


def test_aspect_sans_passage_transmis_ne_produit_pas_de_non_conformite(monkeypatch):
    """Cas non conforme : le LLM tente de rattacher une non-conformite a une reference qui ne
    figure PAS parmi les passages effectivement transmis -> aucune NonConformite produite pour
    cette entree (rejet, jamais de reference inventee, FR-013/FR-019)."""

    def _appel_mocke(prompt, client=None):
        return {
            "secteur_activite": "sante",
            "finalite": "diagnostic assiste",
            "niveau_autonomie_decisionnelle": "supervisee",
            "passages_utilises": [],
            "non_conformites": [
                {
                    "description": "Point invente hors des passages fournis.",
                    "passage_source": "RGPD-ART-INEXISTANT",
                }
            ],
        }

    monkeypatch.setattr(aiact_analyzer.llm_client, "appeler_llm", _appel_mocke)

    profil, non_conformites = aiact_analyzer.analyser(_selection(), PASSAGES)

    assert profil.echec is False
    assert non_conformites == []
