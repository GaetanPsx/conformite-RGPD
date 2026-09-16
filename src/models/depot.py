"""Modeles lies au mode d'entree "depot" (data-model.md DepotCible, ModeEntree)."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, field_validator

GITHUB_REPO_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Retourne (owner, repo) si `url` matche le format GitHub attendu, sinon None."""
    if not isinstance(url, str):
        return None
    match = GITHUB_REPO_URL_RE.match(url.strip())
    if not match:
        return None
    return match.group("owner"), match.group("repo")


class DepotCible(BaseModel):
    """Le depot GitHub public soumis pour evaluation (mode depot). FR-001, FR-002."""

    url: str
    owner: str
    repo: str
    est_public: bool | None = None
    default_branch: str | None = None

    @field_validator("url")
    @classmethod
    def _valider_url(cls, v: str) -> str:
        if parse_github_url(v) is None:
            raise ValueError(
                "url DOIT matcher le format https://github.com/{owner}/{repo} (FR-001)"
            )
        return v


class Mode(str, Enum):
    DEPOT = "depot"
    DOCUMENTATION = "documentation"


class ModeEntree(BaseModel):
    """Resultat du routage d'entree (FR-001, research.md §8)."""

    mode: Mode
    source_ignoree: bool = False
