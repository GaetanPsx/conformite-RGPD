"""Recuperation du contenu d'une documentation de projet fournie via un lien direct.

Variante du mode documentation (FR-001) : au lieu de coller du texte ou de televerser un
fichier, l'utilisateur peut coller l'URL d'une documentation (README brut, page de doc, etc.).
Le contenu est recupere cote serveur puis traite exactement comme une documentation collee.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import httpx

MAX_LIEN_BYTES = 2_000_000  # meme plafond que le televersement de fichier
TIMEOUT_SECONDES = 10.0


class LienDocumentationInvalideError(Exception):
    """Le lien fourni n'est pas une URL http(s) exploitable."""


class LienDocumentationInaccessibleError(Exception):
    """Le contenu du lien n'a pas pu etre recupere (reseau, code HTTP, taille, cible interne)."""


def _hote_est_interne(hote: str) -> bool:
    """Refuse `localhost` et les hotes exprimes comme une IP litterale privee/locale
    (protection SSRF basique, sans resolution DNS : ce module ne doit pas dependre d'un
    acces reseau reel pour etre teste, comme le reste du pipeline)."""
    if hote == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(hote)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast


def recuperer_contenu(url: str) -> bytes:
    """Telecharge le contenu du lien fourni, avec les memes garde-fous que le televersement
    (taille max, timeout) et une protection basique contre les cibles reseau internes."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise LienDocumentationInvalideError("Le lien doit être une URL http(s) valide")

    if _hote_est_interne(parsed.hostname):
        raise LienDocumentationInaccessibleError(
            "Ce lien pointe vers une ressource réseau non autorisée"
        )

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDES, follow_redirects=True) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        raise LienDocumentationInaccessibleError(
            f"Impossible de récupérer le contenu du lien : {exc}"
        ) from exc

    if resp.status_code != 200:
        raise LienDocumentationInaccessibleError(
            f"Le lien a répondu avec le statut {resp.status_code}"
        )

    contenu = resp.content
    if len(contenu) > MAX_LIEN_BYTES:
        raise LienDocumentationInaccessibleError(
            "Le contenu du lien dépasse la taille maximale autorisée (2 Mo)"
        )

    return contenu
