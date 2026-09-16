"""T023/T024 [US1] : cas conforme + cas non conforme pour la selection de fichiers AI Act et RGPD
(FR-004, FR-005, FR-006)."""

from src.models.fichier import FichierDepot
from src.services.file_selector import selectionner_fichiers_aiact, selectionner_fichiers_rgpd


def _lecteur_contenu_factory(mapping: dict[str, str]):
    def lecteur(chemin: str) -> bytes | None:
        val = mapping.get(chemin)
        return val.encode("utf-8") if val is not None else None

    return lecteur


def test_selection_aiact_priorise_readme_et_manifeste_puis_profondeur_puis_alpha():
    fichiers = [
        FichierDepot.depuis_chemin("src/deep/nested/model.py"),
        FichierDepot.depuis_chemin("b_module.py"),
        FichierDepot.depuis_chemin("a_module.py"),
        FichierDepot.depuis_chemin("README.md"),
        FichierDepot.depuis_chemin("requirements.txt"),
    ]
    contenu = {f.chemin: f"contenu de {f.chemin}" for f in fichiers}
    lecteur = _lecteur_contenu_factory(contenu)

    selection = selectionner_fichiers_aiact(fichiers, lecteur_contenu=lecteur)

    chemins = [fc.fichier.chemin for fc in selection.fichiers]
    assert chemins[0] == "README.md"
    assert chemins[1] == "requirements.txt"
    # puis profondeur croissante (racine d'abord), puis alphabetique
    assert chemins[2:4] == ["a_module.py", "b_module.py"]
    assert chemins[4] == "src/deep/nested/model.py"
    assert selection.selection_partielle is False


def test_selection_aiact_limite_15_fichiers_et_marque_partielle():
    fichiers = [FichierDepot.depuis_chemin(f"file_{i}.py") for i in range(20)]
    contenu = {f.chemin: "contenu" for f in fichiers}
    lecteur = _lecteur_contenu_factory(contenu)

    selection = selectionner_fichiers_aiact(fichiers, lecteur_contenu=lecteur)

    assert len(selection.fichiers) == 15
    assert selection.selection_partielle is True


def test_selection_aiact_exclut_fichier_binaire_non_decodable():
    fichiers = [
        FichierDepot.depuis_chemin("README.md"),
        FichierDepot.depuis_chemin("model.bin"),
    ]

    def lecteur(chemin: str) -> bytes | None:
        if chemin == "README.md":
            return b"texte lisible"
        return b"\xff\xfe\x00\x01binary-non-utf8-\x80\x81"

    selection = selectionner_fichiers_aiact(fichiers, lecteur_contenu=lecteur)
    chemins = [fc.fichier.chemin for fc in selection.fichiers]
    assert "model.bin" not in chemins
    assert "README.md" in chemins


def test_selection_aiact_tronque_fichier_trop_volumineux_sans_exclure():
    gros_contenu = "x" * 50_000
    fichiers = [FichierDepot.depuis_chemin("README.md")]
    lecteur = _lecteur_contenu_factory({"README.md": gros_contenu})

    selection = selectionner_fichiers_aiact(fichiers, lecteur_contenu=lecteur)
    assert len(selection.fichiers) == 1
    assert selection.fichiers[0].tronque is True
    assert len(selection.fichiers[0].contenu) < len(gros_contenu)


def test_selection_rgpd_priorise_schemas_migrations_fixtures_config():
    fichiers = [
        FichierDepot.depuis_chemin("random_notes.txt"),
        FichierDepot.depuis_chemin("db/schema.sql"),
        FichierDepot.depuis_chemin("config/settings.json"),
        FichierDepot.depuis_chemin("migrations/0001_init.sql"),
        FichierDepot.depuis_chemin("fixtures/users.json"),
    ]
    contenu = {f.chemin: "contenu" for f in fichiers}
    lecteur = _lecteur_contenu_factory(contenu)

    selection = selectionner_fichiers_rgpd(fichiers, lecteur_contenu=lecteur)
    chemins = [fc.fichier.chemin for fc in selection.fichiers]
    assert "random_notes.txt" not in chemins
    assert "db/schema.sql" in chemins
    assert "config/settings.json" in chemins


def test_selection_rgpd_limite_15_fichiers_independamment_de_aiact():
    fichiers = [FichierDepot.depuis_chemin(f"migrations/{i:04d}_migration.sql") for i in range(20)]
    contenu = {f.chemin: "contenu" for f in fichiers}
    lecteur = _lecteur_contenu_factory(contenu)

    selection = selectionner_fichiers_rgpd(fichiers, lecteur_contenu=lecteur)
    assert len(selection.fichiers) == 15
    assert selection.selection_partielle is True
