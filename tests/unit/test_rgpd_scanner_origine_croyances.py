"""T063 [US4] : cas conforme + cas non conforme pour la categorie `origine_croyances`
(mots-cles d'origine ethnique/religion dans des fixtures, FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("fixtures/users.json")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_colonne_origine_ethnique_est_detectee():
    """Cas conforme : une colonne `origine_ethnique` produit une DetectionRgpd
    `origine_croyances`."""
    detections = rgpd_scanner.scanner(
        _selection('{"id": 1, "origine_ethnique": "confidentiel"}')
    )

    detections_origine = [
        d for d in detections if d.categorie == CategorieRgpd.ORIGINE_CROYANCES
    ]
    assert len(detections_origine) == 1
    assert "origine_ethnique" not in detections_origine[0].extrait_masque


def test_texte_sans_mot_cle_origine_croyances_ne_produit_aucune_detection():
    """Cas non conforme : aucun mot-cle d'origine/croyance -> aucune DetectionRgpd."""
    detections = rgpd_scanner.scanner(_selection('{"id": 1, "prix": 9.99}'))

    assert [d for d in detections if d.categorie == CategorieRgpd.ORIGINE_CROYANCES] == []
