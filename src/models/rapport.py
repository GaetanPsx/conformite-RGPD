"""ProfilProjetCombine et RapportFinal (data-model.md ; FR-009, FR-011, FR-012, FR-015, FR-017).

Important (FR-014) : aucun de ces modeles ne porte de champ de score ou de niveau de risque de
conformite agrege global ; seule la liste individuelle de NonConformite est dans le scope.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.models.depot import DepotCible, ModeEntree
from src.models.detection_rgpd import DetectionRgpd
from src.models.documentation import DocumentationFournie
from src.models.non_conformite import NonConformite
from src.models.profil_aiact import ProfilAiAct


class ProfilProjetCombine(BaseModel):
    mode_entree: ModeEntree
    depot: DepotCible | None = None
    documentation: DocumentationFournie | None = None
    profil_aiact: ProfilAiAct
    detections_rgpd: list[DetectionRgpd] = []
    non_conformites: list[NonConformite] = []
    appels_llm_effectues: int = 0
    taille_envoyee_par_appel: list[int] = []
    avertissements: list[str] = []


class RapportFinal(BaseModel):
    profil_combine: ProfilProjetCombine
    citations: list[str] = []
    avertissements: list[str] = []
    format: Literal["html"] = "html"
    telechargeable: bool = True
    html: str | None = None
