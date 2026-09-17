"""T058 [US4] : cas conforme (motif email valide detecte) + cas non conforme (aucun motif) pour
la categorie `contact` (FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("data/contacts.sql")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_motif_email_valide_est_detecte():
    """Cas conforme : un email valide dans le contenu produit une DetectionRgpd `contact`."""
    detections = rgpd_scanner.scanner(
        _selection("INSERT INTO t VALUES ('jean.dupont@example.com');")
    )

    detections_contact = [d for d in detections if d.categorie == CategorieRgpd.CONTACT]
    assert len(detections_contact) == 1
    assert detections_contact[0].source == "data/contacts.sql"
    assert "jean.dupont@example.com" not in detections_contact[0].extrait_masque


def test_texte_sans_motif_email_ne_produit_aucune_detection():
    """Cas non conforme : aucun motif de contact dans le texte -> aucune DetectionRgpd."""
    detections = rgpd_scanner.scanner(_selection("CREATE TABLE produits (id INT, prix FLOAT);"))

    assert [d for d in detections if d.categorie == CategorieRgpd.CONTACT] == []
