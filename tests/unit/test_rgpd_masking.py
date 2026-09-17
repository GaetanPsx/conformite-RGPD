"""T064 [US4] : verifie qu'aucune valeur brute complete n'apparait dans `extrait_masque` pour
chacune des 6 categories RGPD (FR-010a) : la valeur d'entree connue n'est jamais une sous-chaine
exacte du masque produit."""

import pytest

from src.models.detection_rgpd import CategorieRgpd
from src.services.rgpd_masking import masquer

VALEURS_PAR_CATEGORIE = {
    CategorieRgpd.IDENTITE: "Jean Dupont",
    CategorieRgpd.CONTACT: "jean.dupont@example.com",
    CategorieRgpd.IDENTIFIANT_NATIONAL: "185057500123456",
    CategorieRgpd.SANTE: "dossier_medical",
    CategorieRgpd.BIOMETRIE: "reconnaissance_faciale",
    CategorieRgpd.ORIGINE_CROYANCES: "origine_ethnique",
}


@pytest.mark.parametrize("categorie,valeur", list(VALEURS_PAR_CATEGORIE.items()))
def test_valeur_brute_jamais_dans_le_masque(categorie, valeur):
    masque = masquer(categorie, valeur)

    assert valeur not in masque
    assert masque != valeur
