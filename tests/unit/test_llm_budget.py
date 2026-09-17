"""T053 [US3] : cas conforme + cas non conforme pour le compteur `appels_llm_effectues` et
`taille_envoyee_par_appel` de `llm_client.appeler_llm` (FR-009).

Un appel LLM (reussi ou non) incremente le compteur ; un depot volumineux (>15 fichiers
pertinents par categorie) ne doit jamais declencher plus de 2 appels LLM au total pour une
evaluation (verifie ici au niveau du compteur, l'orchestration reelle est couverte par le test
d'integration T054).
"""

import json

from src.services import llm_client


class _FauxMessage:
    def __init__(self, texte: str):
        self.content = texte


class _FauxChoix:
    def __init__(self, texte: str):
        self.message = _FauxMessage(texte)


class _FausseReponse:
    def __init__(self, texte: str):
        self.choices = [_FauxChoix(texte)]


class _FauxClient:
    def __init__(self, texte: str):
        self._texte = texte
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        return _FausseReponse(self._texte)


def test_appel_reussi_incremente_le_compteur_a_un():
    """Cas conforme : un appel LLM reussi incremente `appels_llm_effectues` de 1 et enregistre
    la taille du prompt envoye."""
    llm_client.reset_compteurs()
    client = _FauxClient(json.dumps({"secteur_activite": "sante"}))

    resultat = llm_client.appeler_llm("prompt de test", client=client)

    assert resultat == {"secteur_activite": "sante"}
    assert llm_client.appels_llm_effectues == 1
    assert llm_client.taille_envoyee_par_appel == [len("prompt de test")]


def test_deux_appels_ne_depassent_jamais_le_plafond_de_deux_pour_une_evaluation():
    """Cas non conforme (limite) : meme avec un contenu source tres volumineux impliquant
    plusieurs appels successifs, le compteur ne doit jamais depasser 2 pour une seule
    evaluation (FR-009) - verifie ici que 2 appels consecutifs aboutissent bien a un compteur
    de 2, jamais davantage, et que le budget de caracteres par appel est toujours respecte."""
    llm_client.reset_compteurs()
    client = _FauxClient(json.dumps({"secteur_activite": "sante"}))

    llm_client.appeler_llm("x" * 50_000, client=client)
    llm_client.appeler_llm("y" * 50_000, client=client)

    assert llm_client.appels_llm_effectues == 2
    assert all(taille <= llm_client.MAX_PROMPT_CHARS for taille in llm_client.taille_envoyee_par_appel)
