"""Selection bornee et deterministe de fichiers pour AI Act et RGPD (FR-004, FR-005, FR-006).

Regle de priorite (FR-006, clarification du 2026-09-16) :
    (1) README et manifeste de dependances en premier (pour AI Act) / fichiers RGPD-pertinents
        prioritaires (schemas SQL, migrations, fixtures, config JSON) pour RGPD ;
    (2) puis les fichiers restants tries par profondeur de chemin croissante (racine d'abord) ;
    (3) puis, a profondeur egale, par ordre alphabetique du chemin complet.

Un fichier binaire ou non decodable en UTF-8 est exclu. Un fichier decodable en texte mais qui
depasse, a lui seul, le plafond de contenu par appel LLM est tronque (jamais exclu pour ce seul
motif).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from src.models.fichier import FichierAvecContenu, FichierDepot
from src.models.selection import MAX_FICHIERS_PAR_CATEGORIE, SelectionAiAct, SelectionRgpd

# Plafond applique a un fichier individuel avant envoi/scan (aligne sur FR-008, 40 000 caracteres
# au total pour l'appel LLM ; un seul fichier ne doit pas depasser ce plafond a lui seul).
MAX_CARACTERES_PAR_FICHIER = 40_000
NB_THREADS_TELECHARGEMENT = 8

README_NAMES = {"readme", "readme.md", "readme.rst", "readme.txt"}
MANIFESTE_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "pipfile",
    "poetry.lock",
    "setup.py",
    "setup.cfg",
    "go.mod",
    "cargo.toml",
    "gemfile",
}

RGPD_KEYWORDS = ("schema", "migration", "fixture", "config", "seed")
RGPD_EXTENSIONS = {".sql", ".json"}

BINARY_EXTENSIONS = {
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".exe",
    ".so",
    ".dll",
    ".zip",
    ".tar",
    ".gz",
    ".pt",
    ".pth",
    ".onnx",
    ".woff",
    ".woff2",
    ".ico",
}


def _est_readme_ou_manifeste(chemin: str) -> bool:
    nom = chemin.rsplit("/", 1)[-1].lower()
    return nom in README_NAMES or nom in MANIFESTE_NAMES


def _cle_tri_priorite(fichier: FichierDepot) -> tuple:
    prioritaire = 0 if _est_readme_ou_manifeste(fichier.chemin) else 1
    return (prioritaire, fichier.profondeur, fichier.chemin)


def _cle_tri_rgpd(fichier: FichierDepot) -> tuple:
    prioritaire = 0 if _est_pertinent_rgpd(fichier.chemin) else 1
    return (prioritaire, fichier.profondeur, fichier.chemin)


def _est_pertinent_rgpd(chemin: str) -> bool:
    chemin_lower = chemin.lower()
    nom = chemin_lower.rsplit("/", 1)[-1]
    if any(kw in chemin_lower for kw in RGPD_KEYWORDS):
        return True
    ext = "." + nom.rsplit(".", 1)[-1] if "." in nom else ""
    return ext in RGPD_EXTENSIONS


def _lire_et_tronquer(
    fichier: FichierDepot, lecteur_contenu: Callable[[str], bytes | None]
) -> FichierAvecContenu | None:
    ext = (fichier.extension or "").lower()
    if ext in BINARY_EXTENSIONS:
        return None
    brut = lecteur_contenu(fichier.chemin)
    if brut is None:
        return None
    try:
        texte = brut.decode("utf-8")
    except UnicodeDecodeError:
        return None
    tronque = len(texte) > MAX_CARACTERES_PAR_FICHIER
    if tronque:
        texte = texte[:MAX_CARACTERES_PAR_FICHIER]
    return FichierAvecContenu(fichier=fichier, contenu=texte, tronque=tronque)


def _selectionner(
    fichiers: list[FichierDepot],
    cle_tri: Callable[[FichierDepot], tuple],
    lecteur_contenu: Callable[[str], bytes | None],
    limite: int,
) -> tuple[list[FichierAvecContenu], bool]:
    fichiers_tries = sorted(fichiers, key=cle_tri)

    # Les telechargements sont du reseau pur : on prefetch en parallele les `limite` premiers
    # candidats (cas nominal), le reste eventuel (fichiers introuvables/illisibles) est lu a la
    # demande. Les lectures sont memoisees pour qu'un meme fichier ne soit jamais telecharge deux fois.
    with ThreadPoolExecutor(max_workers=NB_THREADS_TELECHARGEMENT) as pool:
        prefetch = {
            f.chemin: pool.submit(lecteur_contenu, f.chemin) for f in fichiers_tries[:limite]
        }

    def lecteur_memoise(chemin: str) -> bytes | None:
        if chemin in prefetch:
            return prefetch[chemin].result()
        return lecteur_contenu(chemin)

    selectionnes: list[FichierAvecContenu] = []
    for f in fichiers_tries:
        if len(selectionnes) >= limite:
            break
        avec_contenu = _lire_et_tronquer(f, lecteur_memoise)
        if avec_contenu is not None:
            selectionnes.append(avec_contenu)
    selection_partielle = len(fichiers_tries) > len(selectionnes)
    return selectionnes, selection_partielle


def selectionner_fichiers_aiact(
    fichiers: list[FichierDepot],
    lecteur_contenu: Callable[[str], bytes | None],
    limite: int = MAX_FICHIERS_PAR_CATEGORIE,
) -> SelectionAiAct:
    selectionnes, selection_partielle = _selectionner(
        fichiers, _cle_tri_priorite, lecteur_contenu, limite
    )
    taille_totale = sum(len(fc.contenu) for fc in selectionnes)
    return SelectionAiAct(
        fichiers=selectionnes,
        selection_partielle=selection_partielle,
        taille_totale_caracteres=taille_totale,
    )


def selectionner_fichiers_rgpd(
    fichiers: list[FichierDepot],
    lecteur_contenu: Callable[[str], bytes | None],
    limite: int = MAX_FICHIERS_PAR_CATEGORIE,
) -> SelectionRgpd:
    fichiers_pertinents = [f for f in fichiers if _est_pertinent_rgpd(f.chemin)]
    selectionnes, selection_partielle = _selectionner(
        fichiers_pertinents, _cle_tri_rgpd, lecteur_contenu, limite
    )
    return SelectionRgpd(fichiers=selectionnes, selection_partielle=selection_partielle)
