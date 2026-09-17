"""T060 [US4] : cas conforme + cas non conforme pour la categorie `identifiant_national` (numero
de securite sociale francais, FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("data/schema.sql")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_numero_securite_sociale_valide_est_detecte():
    """Cas conforme : un numero de securite sociale francais (13 chiffres + cle) produit une
    DetectionRgpd `identifiant_national`."""
    numero_nir = "185057500123456"
    detections = rgpd_scanner.scanner(_selection(f"-- exemple NIR: {numero_nir}"))

    detections_national = [
        d for d in detections if d.categorie == CategorieRgpd.IDENTIFIANT_NATIONAL
    ]
    assert len(detections_national) == 1
    assert numero_nir not in detections_national[0].extrait_masque
    # Deux derniers chiffres visibles (research.md §5).
    assert detections_national[0].extrait_masque.endswith("56")


def test_texte_sans_numero_national_ne_produit_aucune_detection():
    """Cas non conforme : aucun numero de securite sociale dans le texte -> aucune
    DetectionRgpd."""
    detections = rgpd_scanner.scanner(_selection("CREATE TABLE produits (id INT, prix FLOAT);"))

    assert [d for d in detections if d.categorie == CategorieRgpd.IDENTIFIANT_NATIONAL] == []
