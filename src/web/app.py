"""Application FastAPI : formulaire, orchestration du pipeline, affichage du rapport (US1).

Aucune persistance serveur (FR-017) : tout l'etat vit dans la duree de la requete HTTP.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.models.documentation import DocumentationFournie, SourceDocumentation
from src.models.fichier import FichierAvecContenu, FichierDepot
from src.models.selection import SelectionAiAct, SelectionRgpd
from src.services import (
    aiact_analyzer,
    doc_link_fetcher,
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
STATIC_DIR = Path(__file__).resolve().parent / "static"

@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Precharge le modele d'embedding local au demarrage plutot qu'a la premiere requete
    # /evaluate, pour eviter de faire payer le cold start (chargement des poids) a l'utilisateur.
    try:
        index = retriever._charger_index()
        retriever._charger_modele(index["model_name"])
    except FileNotFoundError:
        pass
    yield


app = FastAPI(title="Pipeline d'analyse de conformite AI Act / RGPD", lifespan=_lifespan)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

MAX_DOC_CHARS = 40_000
MAX_UPLOAD_BYTES = 2_000_000  # 2 Mo : evite l'epuisement memoire par upload volumineux
MAX_BODY_BYTES = 3_000_000  # 3 Mo : plafond global du corps de requete (fichier + champs form)


@app.middleware("http")
async def _limiter_taille_corps(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            taille = int(content_length)
        except ValueError:
            taille = None
        if taille is not None and taille > MAX_BODY_BYTES:
            return _erreur(
                request,
                "La requête dépasse la taille maximale autorisée (3 Mo).",
                status_code=413,
            )
    return await call_next(request)

# Rate limiting basique par IP (evite l'abus de l'appel LLM payant / de l'API GitHub, FR non couvert
# par le spec initial mais necessaire en exposition publique). Etat en memoire, suffisant pour une
# instance unique ; a remplacer par un store partage en cas de scaling horizontal.
RATE_LIMIT_MAX_REQUETES = 10
RATE_LIMIT_FENETRE_SECONDES = 60.0
_historique_requetes: dict[str, deque[float]] = defaultdict(deque)


def _verifier_rate_limit(client_ip: str) -> None:
    maintenant = time.monotonic()
    historique = _historique_requetes[client_ip]
    while historique and maintenant - historique[0] > RATE_LIMIT_FENETRE_SECONDES:
        historique.popleft()
    if len(historique) >= RATE_LIMIT_MAX_REQUETES:
        raise HTTPException(
            status_code=429,
            detail="Trop de requêtes. Réessayez dans une minute.",
        )
    historique.append(maintenant)


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
    documentation_lien: str | None = Form(default=None),
    documentation_fichier: UploadFile | None = None,
):
    client_ip = request.client.host if request.client else "inconnu"
    _verifier_rate_limit(client_ip)

    fichier_bytes: bytes | None = None
    nom_fichier: str | None = None
    if documentation_fichier is not None and getattr(documentation_fichier, "filename", None):
        fichier_bytes = documentation_fichier.file.read(MAX_UPLOAD_BYTES + 1)
        if len(fichier_bytes) > MAX_UPLOAD_BYTES:
            return _erreur(
                request,
                "Le fichier téléversé dépasse la taille maximale autorisée (2 Mo).",
                status_code=413,
            )
        nom_fichier = documentation_fichier.filename
        if not fichier_bytes:
            fichier_bytes = None

    try:
        mode_entree = input_router.determiner_mode(
            repo_url=repo_url,
            documentation_texte=documentation_texte,
            documentation_fichier=fichier_bytes,
            documentation_lien=documentation_lien,
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
        lien_documentation = (documentation_lien or "").strip()
        if fichier_bytes:
            source = SourceDocumentation.FICHIER_TELEVERSE
            contenu_brut: bytes | str = fichier_bytes
        elif documentation_texte and documentation_texte.strip():
            source = SourceDocumentation.TEXTE_COLLE
            contenu_brut = documentation_texte
        else:
            try:
                contenu_brut = doc_link_fetcher.recuperer_contenu(lien_documentation)
            except doc_link_fetcher.LienDocumentationInvalideError as exc:
                return _erreur(request, str(exc), status_code=422)
            except doc_link_fetcher.LienDocumentationInaccessibleError as exc:
                return _erreur(request, str(exc), status_code=422)
            source = SourceDocumentation.LIEN_URL
            nom_fichier = lien_documentation

        if isinstance(contenu_brut, bytes):
            try:
                contenu_texte = contenu_brut.decode("utf-8")
            except UnicodeDecodeError:
                message_erreur = (
                    "Le contenu récupéré depuis le lien n'est pas un format texte exploitable "
                    "(binaire)."
                    if source == SourceDocumentation.LIEN_URL
                    else "Le fichier téléversé n'est pas un format texte exploitable (binaire)."
                )
                return _erreur(request, message_erreur, status_code=422)
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

    profil_aiact, non_conformites_aiact = aiact_analyzer.analyser(selection_aiact, passages)
    detections_rgpd = rgpd_scanner.scanner(selection_rgpd)
    non_conformites_rgpd = rgpd_scanner.associer_non_conformites(detections_rgpd)

    profil_combine = report_builder.combiner(
        mode_entree=mode_entree,
        depot=depot,
        documentation=documentation,
        profil_aiact=profil_aiact,
        detections_rgpd=detections_rgpd,
        non_conformites=non_conformites_aiact + non_conformites_rgpd,
        appels_llm=llm_client.appels_llm_effectues,
        tailles_envoyees=llm_client.taille_envoyee_par_appel,
        arborescence_tronquee=arborescence_tronquee,
    )
    rapport = report_builder.rendre_html(profil_combine)
    return HTMLResponse(content=rapport.html, status_code=200)


@app.post("/evaluate/download", response_class=HTMLResponse)
def post_evaluate_download(corps_html: str = Form(...)):
    """Telecharge le rapport de l'evaluation qui vient d'etre traitee (FR-001b, US5) : le corps
    deja rendu par `POST /evaluate` est renvoye tel quel en piece jointe, sans aucune ecriture
    serveur ni persistance (FR-017) ; aucun rapport passe n'est recuperable en dehors de ce
    cycle requete/reponse."""
    html = report_builder.envelopper_telechargement(corps_html)
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={"Content-Disposition": 'attachment; filename="rapport-conformite.html"'},
    )
