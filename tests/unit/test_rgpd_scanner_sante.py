"""T061 [US4] : cas conforme + cas non conforme pour la categorie `sante` (mots-cles/colonnes de
donnees de sante dans un schema, FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("db/schema.sql")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_colonne_dossier_medical_est_detectee():
    """Cas conforme : une colonne `dossier_medical` produit une DetectionRgpd `sante`."""
    detections = rgpd_scanner.scanner(
        _selection("CREATE TABLE patients (id INT, dossier_medical TEXT);")
    )

    detections_sante = [d for d in detections if d.categorie == CategorieRgpd.SANTE]
    assert len(detections_sante) == 1
    assert "dossier_medical" not in detections_sante[0].extrait_masque


def test_texte_sans_mot_cle_sante_ne_produit_aucune_detection():
    """Cas non conforme : aucun mot-cle de sante -> aucune DetectionRgpd."""
    detections = rgpd_scanner.scanner(
        _selection("CREATE TABLE produits (id INT, prix FLOAT);")
    )

    assert [d for d in detections if d.categorie == CategorieRgpd.SANTE] == []
