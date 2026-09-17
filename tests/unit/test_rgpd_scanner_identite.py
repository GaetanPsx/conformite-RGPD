"""T059 [US4] : cas conforme + cas non conforme pour la categorie `identite` (nom complet
associe a un identifiant structure, FR-010, SC-005)."""

from src.models.fichier import FichierDepot, FichierAvecContenu
from src.models.detection_rgpd import CategorieRgpd
from src.models.selection import SelectionRgpd
from src.services import rgpd_scanner


def _selection(contenu: str) -> SelectionRgpd:
    fichier = FichierDepot.depuis_chemin("data/fixtures.json")
    fc = FichierAvecContenu(fichier=fichier, contenu=contenu, tronque=False)
    return SelectionRgpd(fichiers=[fc], selection_partielle=False)


def test_colonne_nom_complet_structuree_est_detectee():
    """Cas conforme : une colonne structuree `nom_complet: "Jean Dupont"` produit une
    DetectionRgpd `identite`."""
    detections = rgpd_scanner.scanner(_selection('nom_complet: "Jean Dupont"'))

    detections_identite = [d for d in detections if d.categorie == CategorieRgpd.IDENTITE]
    assert len(detections_identite) == 1
    assert "Jean Dupont" not in detections_identite[0].extrait_masque


def test_texte_sans_colonne_identite_ne_produit_aucune_detection():
    """Cas non conforme : aucune colonne structuree d'identite -> aucune DetectionRgpd."""
    detections = rgpd_scanner.scanner(_selection('quantite: 42, prix: 9.99'))

    assert [d for d in detections if d.categorie == CategorieRgpd.IDENTITE] == []
