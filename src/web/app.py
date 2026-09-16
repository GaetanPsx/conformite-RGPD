"""Application FastAPI : formulaire, orchestration du pipeline, affichage du rapport (US1).

Aucune persistance serveur (FR-017) : tout l'etat vit dans la duree de la requete HTTP.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.models.documentation import DocumentationFournie, SourceDocumentation
from src.models.fichier import FichierAvecContenu, FichierDepot
from src.models.selection import SelectionAiAct, SelectionRgpd
from src.services import (
    aiact_analyzer,
    file_selector,
    github_client,
    input_router,
    legal_corpus,
    llm_client,
    report_builder,
    rgpd_scanner,
)
from src.services.legal_rag import retriever

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

app = FastAPI(title="Pipeline d'analyse de conformite AI Act / RGPD")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

MAX_DOC_CHARS = 40_000


@app.get("/", response_class=HTMLResponse)
def get_root(request: Request):
    return templates.TemplateResponse(request, "formulaire.html", {})


def _erreur(request: Request, message: str, status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "erreur.html", {"message": message}, status_code=status_code
    )


def _construire_selection_documentation(doc: DocumentationFournie) -> tuple[SelectionAiAct, SelectionRgpd]:
    contenu = doc.contenu
    if len(contenu) > MAX_DOC_CHARS:
        contenu = contenu[:MAX_DOC_CHARS]
        doc = doc.model_copy(update={"tronque": True})
    fc = FichierAvecContenu(fichier=doc, contenu=contenu, tronque=doc.tronque)
    selection_aiact = SelectionAiAct(
        fichiers=[fc], selection_partielle=False, taille_totale_caracteres=len(contenu)
    )
    selection_rgpd = SelectionRgpd(fichiers=[fc], selection_partielle=False)
    return selection_aiact, selection_rgpd


@app.post("/evaluate", response_class=HTMLResponse)
def post_evaluate(
    request: Request,
    repo_url: str | None = Form(default=None),
    documentation_texte: str | None = Form(default=None),
    documentation_fichier: UploadFile | None = None,
):
    fichier_bytes: bytes | None = None
    nom_fichier: str | None = None
    if documentation_fichier is not None and getattr(documentation_fichier, "filename", None):
        fichier_bytes = documentation_fichier.file.read()
        nom_fichier = documentation_fichier.filename
        if not fichier_bytes:
            fichier_bytes = None

    try:
        mode_entree = input_router.determiner_mode(
            repo_url=repo_url,
            documentation_texte=documentation_texte,
            documentation_fichier=fichier_bytes,
        )
    except input_router.AucuneEntreeExploitableError as exc:
        return _erreur(request, str(exc), status_code=422)

    llm_client.reset_compteurs()
    depot = None
    documentation = None
    arborescence_tronquee = False

    if mode_entree.mode.value == "depot":
        from src.models.depot import parse_github_url

        owner, repo = parse_github_url(repo_url)
        with httpx.Client(timeout=15.0) as http_client:
            try:
                depot = github_client.verifier_accessibilite(owner, repo, client=http_client)
            except github_client.DepotInaccessibleError:
                return _erreur(
                    request,
                    f"Le dépôt {owner}/{repo} est introuvable ou privé. Seuls les dépôts "
                    "publics et accessibles sans authentification sont pris en charge.",
                )
            except github_client.GitHubRateLimitError:
                return _erreur(
                    request,
                    "L'API GitHub a limité le débit des requêtes non authentifiées. "
                    "Réessayez plus tard.",
                )

            try:
                fichiers, truncated = github_client.lister_fichiers(depot, client=http_client)
            except github_client.GitHubRateLimitError:
                return _erreur(
                    request,
                    "L'API GitHub a limité le débit des requêtes non authentifiées. "
                    "Réessayez plus tard.",
                )
            except github_client.DepotInaccessibleError:
                return _erreur(request, f"Impossible de lister les fichiers de {owner}/{repo}.")

            arborescence_tronquee = truncated

            def lecteur_contenu(chemin: str, _depot=depot, _client=http_client) -> bytes | None:
                return github_client.obtenir_contenu_fichier(_depot, chemin, client=_client)

            selection_aiact = file_selector.selectionner_fichiers_aiact(
                fichiers, lecteur_contenu=lecteur_contenu
            )
            selection_rgpd = file_selector.selectionner_fichiers_rgpd(
                fichiers, lecteur_contenu=lecteur_contenu
            )
    else:
        source = (
            SourceDocumentation.FICHIER_TELEVERSE
            if fichier_bytes
            else SourceDocumentation.TEXTE_COLLE
        )
        contenu_brut = fichier_bytes if fichier_bytes else (documentation_texte or "")
        if isinstance(contenu_brut, bytes):
            try:
                contenu_texte = contenu_brut.decode("utf-8")
            except UnicodeDecodeError:
                return _erreur(
                    request,
                    "Le fichier téléversé n'est pas un format texte exploitable (binaire).",
                    status_code=422,
                )
        else:
            contenu_texte = contenu_brut

        if not contenu_texte or not contenu_texte.strip():
            return _erreur(
                request, "La documentation fournie est vide ou illisible.", status_code=422
            )

        documentation = DocumentationFournie(
            source=source, contenu=contenu_texte, nom_fichier=nom_fichier
        )
        selection_aiact, selection_rgpd = _construire_selection_documentation(documentation)

    # Recherche legale (RAG), 0 appel LLM payant (FR-018/019)
    requete_rag = " ".join(fc.contenu for fc in selection_aiact.fichiers)[:2000]
    passages = retriever.rechercher(requete_rag) if requete_rag.strip() else []

    profil_aiact = aiact_analyzer.analyser(selection_aiact, passages)
    detections_rgpd = rgpd_scanner.scanner(selection_rgpd)

    profil_combine = report_builder.combiner(
        mode_entree=mode_entree,
        depot=depot,
        documentation=documentation,
        profil_aiact=profil_aiact,
        detections_rgpd=detections_rgpd,
        non_conformites=[],
        appels_llm=llm_client.appels_llm_effectues,
        tailles_envoyees=llm_client.taille_envoyee_par_appel,
        arborescence_tronquee=arborescence_tronquee,
    )
    rapport = report_builder.rendre_html(profil_combine)
    return HTMLResponse(content=rapport.html, status_code=200)
