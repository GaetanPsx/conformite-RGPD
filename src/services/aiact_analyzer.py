"""Construction du prompt + appel LLM unique produisant le profil AI Act (FR-007/008/019).

L'appel est fait avec temperature 0 (research.md §3). Le prompt cumule le contenu source
(selection AI Act) et les passages RAG recuperes, tronque en priorite le contenu source pour
respecter le plafond de 40 000 caracteres (FR-008, research.md §7 consequence).
"""

from __future__ import annotations

from src.models.legal_corpus import PassageLegalRecupere
from src.models.non_conformite import NonConformite, OrigineNonConformite
from src.models.profil_aiact import NiveauAutonomieDecisionnelle, ProfilAiAct
from src.models.selection import SelectionAiAct
from src.services import llm_client

MAX_PROMPT_CHARS = 40_000

VALEURS_AUTONOMIE_VALIDES = {v.value for v in NiveauAutonomieDecisionnelle}

PROMPT_TEMPLATE = """Tu es un assistant d'analyse de conformite. A partir du CONTENU SOURCE \
ci-dessous (code/documentation d'un projet), et des PASSAGES LEGAUX fournis (AI Act / RGPD), \
deduis :
- secteur_activite (string courte)
- finalite (string courte, la finalite du systeme)
- niveau_autonomie_decisionnelle : EXACTEMENT une de ces 4 valeurs : \
"aucune", "assistee", "supervisee", "autonome"
- non_conformites : une liste (eventuellement vide) de points de non-conformite potentiels, \
chacun rattache EXPLICITEMENT a un id_reference parmi les PASSAGES LEGAUX fournis ci-dessous \
(jamais une reference inventee ou absente de cette liste)

Reponds UNIQUEMENT avec un objet JSON valide de la forme :
{{"secteur_activite": "...", "finalite": "...", "niveau_autonomie_decisionnelle": "...", \
"passages_utilises": ["id_reference", ...], \
"non_conformites": [{{"description": "...", "passage_source": "id_reference"}}, ...]}}

`passages_utilises` et chaque `passage_source` DOIVENT contenir uniquement des id_reference \
parmi ceux listes ci-dessous. Si aucun passage ne justifie un point de non-conformite, \
`non_conformites` DOIT rester une liste vide plutot que d'inventer une reference.

PASSAGES LEGAUX (id_reference: texte):
{passages}

CONTENU SOURCE:
{contenu}
"""


def construire_prompt(selection: SelectionAiAct, passages: list[PassageLegalRecupere]) -> str:
    """Tronque en priorite le contenu source pour respecter le plafond cumule (FR-008)."""
    passages_texte = "\n".join(f"- {p.id_reference}: {p.texte}" for p in passages)
    contenu_source = "\n\n".join(
        f"--- {getattr(fc.fichier, 'chemin', 'documentation')} ---\n{fc.contenu}"
        for fc in selection.fichiers
    )

    gabarit_vide = PROMPT_TEMPLATE.format(passages=passages_texte, contenu="")
    budget_contenu = max(0, MAX_PROMPT_CHARS - len(gabarit_vide))
    if len(contenu_source) > budget_contenu:
        contenu_source = contenu_source[:budget_contenu]

    return PROMPT_TEMPLATE.format(passages=passages_texte, contenu=contenu_source)


def _extraire_non_conformites(
    reponse: dict, passages_valides: set[str]
) -> list[NonConformite]:
    """Parse `non_conformites` de la reponse LLM, en rejetant toute entree dont le
    `passage_source` ne figure pas parmi les passages effectivement transmis au LLM
    (FR-013/FR-019) ou dont la structure est inexploitable."""
    non_conformites: list[NonConformite] = []
    for entree in reponse.get("non_conformites", []) or []:
        if not isinstance(entree, dict):
            continue
        passage_source = entree.get("passage_source")
        description = entree.get("description")
        if passage_source not in passages_valides:
            continue
        try:
            non_conformites.append(
                NonConformite(
                    description=description or "",
                    passage_source=passage_source,
                    origine=OrigineNonConformite.PROFIL_AIACT,
                )
            )
        except ValueError:
            continue
    return non_conformites


def analyser(
    selection: SelectionAiAct, passages: list[PassageLegalRecupere]
) -> tuple[ProfilAiAct, list[NonConformite]]:
    """Appelle le LLM (unique appel, FR-007) et parse la reponse en (ProfilAiAct,
    list[NonConformite]).

    `echec=True` si la reponse est invalide/vide/inexploitable ou si la valeur d'autonomie
    n'est pas l'une des 4 valeurs fermees attendues (FR-007a, Edge Cases). Dans ce cas, aucune
    non-conformite n'est produite.
    """
    prompt = construire_prompt(selection, passages)
    reponse = llm_client.appeler_llm(prompt)

    fichiers_source = [
        getattr(fc.fichier, "chemin", "documentation") for fc in selection.fichiers
    ]

    if reponse is None:
        return ProfilAiAct(echec=True, fichiers_source=fichiers_source), []

    autonomie_brute = reponse.get("niveau_autonomie_decisionnelle")
    if autonomie_brute not in VALEURS_AUTONOMIE_VALIDES:
        return ProfilAiAct(echec=True, fichiers_source=fichiers_source), []

    passages_valides = {p.id_reference for p in passages}
    passages_utilises = [
        ref for ref in reponse.get("passages_utilises", []) if ref in passages_valides
    ]
    non_conformites = _extraire_non_conformites(reponse, passages_valides)

    profil = ProfilAiAct(
        secteur_activite=reponse.get("secteur_activite"),
        finalite=reponse.get("finalite"),
        niveau_autonomie_decisionnelle=NiveauAutonomieDecisionnelle(autonomie_brute),
        fichiers_source=fichiers_source,
        passages_utilises=passages_utilises,
        echec=False,
    )
    return profil, non_conformites
