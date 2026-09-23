"""Client API GitHub publique non authentifiee (FR-002, FR-003, FR-003a ; research.md §2)."""

from __future__ import annotations

import httpx

from src.models.depot import DepotCible
from src.models.fichier import FichierDepot

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


class DepotInaccessibleError(Exception):
    """Depot introuvable ou prive (404)."""


class GitHubRateLimitError(Exception):
    """Limitation de debit de l'API GitHub non authentifiee (403/429)."""


def verifier_accessibilite(owner: str, repo: str, client: httpx.Client | None = None) -> DepotCible:
    """Appelle GET /repos/{owner}/{repo} pour verifier l'existence/visibilite du depot.

    Leve DepotInaccessibleError si le depot est prive/inexistant (404), et GitHubRateLimitError
    si l'API GitHub limite le debit (403/429), afin de distinguer clairement les deux causes.
    """
    close_client = client is None
    client = client or httpx.Client(timeout=10.0, follow_redirects=True)
    try:
        resp = client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")
        if resp.status_code == 404:
            raise DepotInaccessibleError(f"Depot {owner}/{repo} introuvable ou prive")
        if resp.status_code in (403, 429):
            raise GitHubRateLimitError(
                "Limitation de debit de l'API GitHub non authentifiee, reessayer plus tard"
            )
        resp.raise_for_status()
        data = resp.json()
        est_public = not data.get("private", True)
        if not est_public:
            raise DepotInaccessibleError(f"Depot {owner}/{repo} est prive")
        return DepotCible(
            url=f"https://github.com/{owner}/{repo}",
            owner=owner,
            repo=repo,
            est_public=est_public,
            default_branch=data.get("default_branch", "main"),
        )
    finally:
        if close_client:
            client.close()


def obtenir_contenu_fichier(
    depot: DepotCible, chemin: str, client: httpx.Client | None = None
) -> bytes | None:
    """Recupere le contenu brut d'un fichier via raw.githubusercontent.com (pas d'authentification
    requise). Retourne None si le fichier est introuvable ou inaccessible, plutot que de lever."""
    close_client = client is None
    client = client or httpx.Client(timeout=15.0, follow_redirects=True)
    try:
        branch = depot.default_branch or "main"
        resp = client.get(f"{GITHUB_RAW_BASE}/{depot.owner}/{depot.repo}/{branch}/{chemin}")
        if resp.status_code != 200:
            return None
        return resp.content
    except httpx.HTTPError:
        return None
    finally:
        if close_client:
            client.close()


def lister_fichiers(
    depot: DepotCible, client: httpx.Client | None = None
) -> tuple[list[FichierDepot], bool]:
    """Appelle GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1 sans telecharger le contenu.

    Retourne (fichiers, truncated) ou `truncated` est le booleen renvoye par l'API GitHub lorsque
    l'arborescence depasse la limite de l'endpoint (FR-003a).
    """
    close_client = client is None
    client = client or httpx.Client(timeout=15.0, follow_redirects=True)
    try:
        branch = depot.default_branch or "main"
        resp = client.get(
            f"{GITHUB_API_BASE}/repos/{depot.owner}/{depot.repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )
        if resp.status_code in (403, 429):
            raise GitHubRateLimitError(
                "Limitation de debit de l'API GitHub non authentifiee, reessayer plus tard"
            )
        if resp.status_code == 404:
            raise DepotInaccessibleError(
                f"Arborescence introuvable pour {depot.owner}/{depot.repo}@{branch}"
            )
        resp.raise_for_status()
        data = resp.json()
        fichiers = [
            FichierDepot.depuis_chemin(item["path"], item.get("size"))
            for item in data.get("tree", [])
            if item.get("type") == "blob"
        ]
        truncated = bool(data.get("truncated", False))
        return fichiers, truncated
    finally:
        if close_client:
            client.close()
