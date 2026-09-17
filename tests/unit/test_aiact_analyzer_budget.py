"""T052 [US3] : cas conforme + cas non conforme pour le plafonnement a 40 000 caracteres dans
`aiact_analyzer.construire_prompt` (FR-008, research.md §7 consequence).

Contenu source + passages RAG cumules <= 40 000 -> envoye tel quel ; depassement -> le contenu
source est tronque en priorite, les passages RAG sont conserves integralement.
"""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.legal_corpus import PassageLegalRecupere
from src.models.selection import SelectionAiAct
from src.services import aiact_analyzer

PASSAGES = [
    PassageLegalRecupere(id_reference="RGPD-ART-9", texte="texte article 9", score_pertinence=0.9),
]


def _selection(contenu: str) -> SelectionAiAct:
    fichier = FichierDepot.depuis_chemin("src/model.py")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionAiAct(
        fichiers=[fc], selection_partielle=False, taille_totale_caracteres=len(contenu)
    )


def test_contenu_sous_le_plafond_envoye_integralement():
    """Cas conforme : contenu source + passages cumules sous 40 000 caracteres -> le contenu
    source n'est pas tronque dans le prompt final."""
    contenu = "x" * 100
    prompt = aiact_analyzer.construire_prompt(_selection(contenu), PASSAGES)

    assert len(prompt) <= aiact_analyzer.MAX_PROMPT_CHARS
    assert "x" * 100 in prompt
    assert "RGPD-ART-9" in prompt
    assert "texte article 9" in prompt


def test_contenu_au_dessus_du_plafond_tronque_le_contenu_source_en_priorite():
    """Cas non conforme : contenu source depassant a lui seul le plafond -> tronque, les
    passages RAG restent presents integralement dans le prompt final."""
    contenu = "y" * 100_000
    prompt = aiact_analyzer.construire_prompt(_selection(contenu), PASSAGES)

    assert len(prompt) <= aiact_analyzer.MAX_PROMPT_CHARS
    assert "y" * 100_000 not in prompt
    assert "RGPD-ART-9" in prompt
    assert "texte article 9" in prompt
