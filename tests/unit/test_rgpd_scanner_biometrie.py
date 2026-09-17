"""T062 [US4] : cas conforme + cas non conforme pour la categorie `biometrie` (colonnes/motifs
d'empreinte, reconnaissance faciale, FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("db/schema.sql")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_colonne_reconnaissance_faciale_est_detectee():
    """Cas conforme : une colonne `reconnaissance_faciale` produit une DetectionRgpd
    `biometrie`."""
    detections = rgpd_scanner.scanner(
        _selection("CREATE TABLE utilisateurs (id INT, reconnaissance_faciale BLOB);")
    )

    detections_biometrie = [d for d in detections if d.categorie == CategorieRgpd.BIOMETRIE]
    assert len(detections_biometrie) == 1
    assert "reconnaissance_faciale" not in detections_biometrie[0].extrait_masque


def test_texte_sans_mot_cle_biometrie_ne_produit_aucune_detection():
    """Cas non conforme : aucun mot-cle de biometrie -> aucune DetectionRgpd."""
    detections = rgpd_scanner.scanner(
        _selection("CREATE TABLE produits (id INT, prix FLOAT);")
    )

    assert [d for d in detections if d.categorie == CategorieRgpd.BIOMETRIE] == []
