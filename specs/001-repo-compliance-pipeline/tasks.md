---

description: "Task list for Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)"
---

# Tasks: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Input**: Design documents from `/specs/001-repo-compliance-pipeline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-interface.md, quickstart.md

**Tests**: Le Principe II (Test-First Verification, NON-NEGOCIABLE) de la constitution impose un cas
conforme et un cas non conforme, écrits avant l'implémentation, pour chaque règle de sélection de
fichiers, de détermination du mode d'entrée, de chacune des 6 catégories RGPD, et de récupération
RAG (plan.md, quickstart.md). Les tâches de test sont donc incluses et non optionnelles pour ce
projet.

**Organization**: Tasks are grouped by user story (US1–US5, spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Include exact file paths in descriptions

## Path Conventions

Projet unique (plan.md, Structure Decision) :

- `src/models/`, `src/services/`, `src/services/legal_rag/`, `src/web/`, `src/web/templates/`, `src/data/legal_corpus/`
- `tests/contract/`, `tests/integration/`, `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialisation du projet Python/FastAPI et de sa structure de base

- [X] T001 Créer l'arborescence du projet (`src/models/`, `src/services/`, `src/services/legal_rag/`,
      `src/web/`, `src/web/templates/`, `src/data/legal_corpus/`, `tests/contract/`,
      `tests/integration/`, `tests/unit/`) avec fichiers `__init__.py` Python pour chaque package
      sous `src/`
- [X] T002 Créer `requirements.txt` à la racine avec `fastapi`, `uvicorn`, `jinja2`,
      `python-multipart` (upload de fichier), `httpx`, `anthropic`, `sentence-transformers`,
      `numpy`, `pytest`, `respx` (plan.md Primary Dependencies, research.md §1/§2/§3/§6/§7)
- [X] T003 [P] Configurer `pyproject.toml` (ou `setup.cfg`) avec `pytest` (chemin `tests/`) et un
      outil de lint/format (ex. `ruff`) pour le projet Python 3.11 (plan.md Technical Context)
- [X] T004 [P] Créer `.env.example` documentant `ANTHROPIC_API_KEY` requis (quickstart.md
      Prérequis), sans valeur réelle committée
- [X] T004a [P] Créer le workflow CI `.github/workflows/tests.yml` exécutant `pytest` (avec
      `respx`, sans appel réseau réel) sur chaque push/PR, conformément à l'exigence de la
      Constitution "Development Workflow & Quality Gates" ("CI MUST run the full rule test suite
      before merge")

**Checkpoint**: Structure du projet prête, dépendances déclarées.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modèles de domaine, corpus juridique statique et infrastructure LLM/GitHub partagés,
bloquants pour toutes les user stories

**⚠️ CRITICAL**: Aucune user story ne peut être commencée avant la fin de cette phase

- [X] T005 [P] Définir les modèles Pydantic `DepotCible` (`url`, `owner`, `repo`, `est_public`,
      `default_branch`) et `ModeEntree` (`mode`: `"depot"`|`"documentation"`, `source_ignoree: bool`)
      dans `src/models/depot.py`, avec validation du champ `url` selon le format
      `https://github.com/{owner}/{repo}` (data-model.md DepotCible, ModeEntree ; FR-001)
- [X] T006 [P] Définir le modèle Pydantic `DocumentationFournie` (`source`: enum
      `"texte_colle"`|`"fichier_televerse"`, `contenu: str` non vide, `nom_fichier: str | None`,
      `tronque: bool`) dans `src/models/documentation.py` (data-model.md DocumentationFournie ;
      FR-001, FR-006a, FR-016)
- [X] T007 [P] Définir les modèles Pydantic `FichierDepot` (`chemin`, `taille_octets: int | None`,
      `extension: str | None`, `profondeur: int`) et `FichierAvecContenu` (`fichier`, `contenu`,
      `tronque: bool`) dans `src/models/fichier.py` (data-model.md FichierDepot, FichierAvecContenu ;
      FR-003)
- [X] T008 [P] Définir les modèles Pydantic `SelectionAiAct` et `SelectionRgpd` (`fichiers:
      list[FichierAvecContenu]`, `selection_partielle: bool`, `taille_totale_caracteres: int` pour
      `SelectionAiAct`) dans `src/models/selection.py`, avec la contrainte "≤ 15 éléments en mode
      dépôt" documentée en docstring (data-model.md SelectionAiAct, SelectionRgpd ; FR-006, FR-006a)
- [X] T009 [P] Définir les modèles Pydantic `PassageLegalRecupere` (`id_reference`, `texte`,
      `score_pertinence: float`) et l'accès en lecture seule `CorpusJuridique` (`id_reference`,
      `texte: str | None`, `theme`, `embedding: list[float] | None`) dans
      `src/models/legal_corpus.py` (data-model.md CorpusJuridique, PassageLegalRecupere ; FR-013,
      FR-018, FR-019)
- [X] T010 [P] Définir les modèles Pydantic `ProfilAiAct` (`secteur_activite: str | None`,
      `finalite: str | None`, `niveau_autonomie_decisionnelle: str | None`,
      `fichiers_source: list[str]`, `passages_utilises: list[str]`, `echec: bool`) dans
      `src/models/profil_aiact.py` (data-model.md ProfilAiAct ; FR-007, FR-014)
- [X] T011 [P] Définir le modèle Pydantic `DetectionRgpd` (`categorie`: enum `identite`, `contact`,
      `identifiant_national`, `sante`, `biometrie`, `origine_croyances`; `source`, `motif`,
      `extrait_masque`) dans `src/models/detection_rgpd.py` (data-model.md DetectionRgpd ; FR-010,
      FR-010a)
- [X] T012 [P] Définir le modèle Pydantic `NonConformite` (`description`, `passage_source:` référence
      à `PassageLegalRecupere.id_reference` DOIT être non `null`, `origine`: enum
      `"profil_aiact"`|`"detection_rgpd"`) dans `src/models/non_conformite.py` (data-model.md
      NonConformite ; FR-007, FR-012, FR-019)
- [X] T013 [US aucune, foundational] Définir les modèles Pydantic `ProfilProjetCombine`
      (`mode_entree`, `depot: DepotCible | None`, `documentation: DocumentationFournie | None`,
      `profil_aiact`, `detections_rgpd: list[DetectionRgpd]`, `non_conformites:
      list[NonConformite]`, `appels_llm_effectues: int` ≤ 2, `taille_envoyee_par_appel: list[int]`)
      et `RapportFinal` (`profil_combine`, `citations: list[str]`, `avertissements: list[str]`,
      `format`: const `"html"`, `telechargeable: bool` toujours `true`) dans
      `src/models/rapport.py` (data-model.md ProfilProjetCombine, RapportFinal ; FR-009, FR-011,
      FR-012, FR-015, FR-017 ; depends on T005-T012)
- [X] T014 Créer le corpus juridique de test minimal (extraits AI Act et RGPD réels couvrant au
      moins : base légale pour données de santé, catégories de données sensibles, obligations de
      transparence pour systèmes à autonomie décisionnelle) en `src/data/legal_corpus/corpus.json`
      (liste d'objets `{id_reference, texte, theme}`), utilisé par `build_index.py` (T015) et par
      les tests (data-model.md CorpusJuridique ; Assumptions spec.md — corpus fourni séparément)
- [X] T015 Implémenter `src/services/legal_rag/build_index.py` : script hors ligne qui charge
      `src/data/legal_corpus/corpus.json`, encode chaque passage avec `sentence-transformers`
      (modèle `paraphrase-multilingual-MiniLM-L12-v2`, research.md §7), et écrit les vecteurs +
      `id_reference` + `texte` dans `src/data/legal_corpus/index.npz` (ou équivalent `.npy`/`.json`
      versionné) ; exécuté une seule fois, jamais à l'exécution d'une évaluation (FR-018,
      research.md §7 ; depends on T014)
- [X] T016 Exécuter `python -m src.services.legal_rag.build_index` pour générer et committer l'index
      vectoriel initial `src/data/legal_corpus/index.npz` (quickstart.md Prérequis ; depends on T015)
- [X] T017 [P] Implémenter `src/services/legal_rag/retriever.py` : charge l'index versionné
      (`index.npz`), encode la requête (texte condensé) avec le même modèle d'embedding local,
      calcule la similarité cosinus via `numpy` contre les vecteurs pré-calculés, et retourne le
      top-N (N borné, ex. 5 à 10) `PassageLegalRecupere` triés par `score_pertinence` décroissant ;
      0 appel LLM (FR-018/FR-019, research.md §7 ; depends on T009, T016)
- [X] T018 [P] Implémenter `src/services/github_client.py` avec `httpx` : fonction
      `verifier_accessibilite(owner, repo) -> DepotCible` appelant `GET
      /repos/{owner}/{repo}` (distingue 404 dépôt privé/inexistant de 403/429 rate limit, research.md
      §2) et fonction `lister_fichiers(depot: DepotCible) -> tuple[list[FichierDepot], bool]`
      appelant `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1` sans télécharger le contenu,
      retournant également le booléen `truncated` renvoyé par l'API GitHub lorsque l'arborescence
      dépasse la limite de l'endpoint (FR-002, FR-003, FR-003a ; depends on T005, T007)
- [X] T019 [P] Implémenter `src/services/input_router.py` : fonction `determiner_mode(repo_url:
      str | None, documentation_texte: str | None, documentation_fichier: bytes | None) ->
      ModeEntree` appliquant la règle "URL GitHub valide → mode dépôt (documentation ignorée et
      signalée via `source_ignoree=true`) ; sinon documentation non vide → mode documentation ;
      sinon rejet" (FR-001, research.md §8 ; depends on T005, T006)
- [X] T020 [P] Implémenter la fonction de masquage déterministe par catégorie RGPD (ex. email →
      `j***@***.com`, numéro national → 2 derniers chiffres visibles) dans
      `src/services/rgpd_masking.py`, appelée immédiatement après chaque détection, avant toute
      autre étape du pipeline (FR-010a, research.md §5 ; depends on T011)
- [X] T021 [P] Implémenter le client LLM `src/services/llm_client.py` encapsulant l'appel unique à
      l'API Anthropic (modèle Haiku, température 0 pour la reproductibilité, research.md §3) :
      fonction `appeler_llm(prompt: str) -> dict | None` retournant `None` (échec) si la réponse
      est vide/malformée/non-JSON, sans lever d'exception non gérée (FR-016 Edge Cases ; ≤40 000
      caractères de prompt, FR-008)

**Checkpoint**: Fondations prêtes — modèles, corpus indexé, clients GitHub/LLM, routage d'entrée et
masquage RGPD disponibles ; l'implémentation des user stories peut commencer.

---

## Phase 3: User Story 1 - Obtenir un rapport de conformité à partir d'un dépôt GitHub ou d'une documentation fournie (Priority: P1) 🎯 MVP

**Goal**: Un utilisateur soumet une URL de dépôt ou une documentation et reçoit un rapport HTML
affiché dans le navigateur, couvrant AI Act et RGPD avec citations légales.

**Independent Test**: Soumettre l'URL d'un dépôt public réel avec code de modèle et fichiers de
données → rapport structuré avec profil AI Act, détections RGPD, citations. Séparément, soumettre
un texte de documentation collé → rapport équivalent sans appel GitHub (quickstart.md Scénarios 1–2).

### Tests for User Story 1 (obligatoire — Principe II)

- [X] T022 [P] [US1] Test unitaire cas conforme + cas non conforme pour `determiner_mode` (URL
      GitHub valide seule → mode dépôt ; documentation seule → mode documentation ; les deux fournis
      → mode dépôt avec `source_ignoree=true` ; ni l'un ni l'autre → erreur) dans
      `tests/unit/test_input_router.py` (FR-001, Edge Cases, Acceptance Scenario US1.6)
- [X] T023 [P] [US1] Test unitaire cas conforme + cas non conforme pour la règle de sélection de
      fichiers AI Act : README/manifeste de dépendances en premier, puis profondeur croissante, puis
      alphabétique ; ≤15 fichiers retenus avec `selection_partielle=true` si dépassement, fichier
      binaire/trop volumineux exclu ou tronqué, dans `tests/unit/test_file_selector.py` (FR-004,
      FR-006 ; depends on T024 module créé — écrit avant l'implémentation)
- [X] T024 [P] [US1] Test unitaire cas conforme + cas non conforme pour la sélection RGPD
      (schémas SQL/migrations/fixtures/config JSON priorisés, même règle de tri, limite 15 fichiers
      indépendante de la sélection AI Act) dans `tests/unit/test_file_selector.py` (FR-005, FR-006)
- [X] T025 [P] [US1] Test unitaire cas conforme + cas non conforme pour la récupération RAG sur
      l'index figé de test (une requête connue retourne un ensemble déterministe de
      `PassageLegalRecupere` ; une requête hors sujet retourne un score de pertinence bas ou une
      liste vide) dans `tests/unit/test_retriever.py`, utilisant `src/data/legal_corpus/index.npz`
      versionné, sans réentraînement (FR-018/FR-019, plan.md Principe II)
- [X] T026 [P] [US1] Test d'intégration : soumission d'une URL de dépôt public (GitHub et LLM mockés
      via `respx`, research.md §6) produisant un rapport avec secteur/finalité/autonomie et au moins
      une citation légale, dans `tests/integration/test_evaluate_repo_mode.py` (Acceptance Scenario
      US1.1, quickstart.md Scénario 1)
- [X] T027 [P] [US1] Test d'intégration : soumission d'un dépôt avec schémas SQL/fixtures produisant
      des détections RGPD avec fichier source, dans `tests/integration/test_evaluate_repo_mode.py`
      (Acceptance Scenario US1.2)
- [X] T028 [P] [US1] Test d'intégration : dépôt sans fichier pertinent AI Act ni RGPD → rapport
      indique explicitement l'absence d'éléments détectés, dans
      `tests/integration/test_evaluate_repo_mode.py` (Acceptance Scenario US1.3)
- [X] T029 [P] [US1] Test d'intégration : soumission de texte de documentation collé (sans
      `repo_url`) → rapport produit, aucun appel `respx` GitHub enregistré, dans
      `tests/integration/test_evaluate_documentation_mode.py` (Acceptance Scenario US1.4,
      quickstart.md Scénario 2, SC-007)
- [X] T030 [P] [US1] Test d'intégration : soumission d'un fichier de documentation téléversé →
      contenu du fichier utilisé comme source unique, dans
      `tests/integration/test_evaluate_documentation_mode.py` (Acceptance Scenario US1.5)
- [X] T031 [P] [US1] Test d'intégration : soumission sans URL valide ni documentation → rejet avec
      message clair, 0 appel GitHub/LLM enregistré, dans
      `tests/integration/test_evaluate_documentation_mode.py` (Acceptance Scenario US1.6)
- [X] T032 [P] [US1] Test contractuel `GET /` retourne 200 avec formulaire contenant `repo_url`,
      `documentation_texte`, `documentation_fichier` dans `tests/contract/test_get_root.py`
      (contracts/web-interface.md GET /)
- [X] T032a [P] [US1] Test unitaire (cas négatif) affirmant qu'aucun champ de score ou de niveau
      de risque de conformité agrégé n'existe sur `ProfilAiAct`, `ProfilProjetCombine` ni
      `RapportFinal` (introspection des modèles Pydantic) et qu'aucune clé de ce type n'apparaît
      dans le HTML rendu par `rendre_html`, dans `tests/unit/test_no_aggregate_risk_score.py`
      (FR-014 — contrainte confirmée explicitement par le commanditaire, spec.md Assumptions)

### Implementation for User Story 1

- [X] T033 [US1] Implémenter `src/services/file_selector.py` : fonctions
      `selectionner_fichiers_aiact(fichiers: list[FichierDepot]) -> SelectionAiAct` et
      `selectionner_fichiers_rgpd(fichiers: list[FichierDepot]) -> SelectionRgpd` appliquant la règle
      de priorité déterministe (README/manifeste d'abord, puis profondeur croissante, puis
      alphabétique), limite de 15 par catégorie ; un fichier binaire ou non décodable en UTF-8 est
      exclu, un fichier décodable en texte mais dépassant à lui seul le plafond de contenu par
      appel LLM est tronqué (jamais exclu pour ce seul motif) (FR-004, FR-005, FR-006, Edge Cases ;
      depends on T007, T008 ; tests T023-T024 doivent échouer avant cette tâche)
- [X] T034 [US1] Implémenter `src/services/legal_corpus.py` : fonction `charger_corpus() ->
      list[CorpusJuridique]` en lecture seule depuis `src/data/legal_corpus/corpus.json` (FR-013 ;
      depends on T009, T014)
- [X] T035 [US1] Implémenter `src/services/aiact_analyzer.py` : fonction `analyser(selection:
      SelectionAiAct, passages: list[PassageLegalRecupere]) -> ProfilAiAct` qui construit le prompt
      (contenu source + passages RAG, priorité de troncature au contenu source, research.md §7),
      demande explicitement au LLM de choisir `niveau_autonomie_decisionnelle` parmi les 4 valeurs
      fermées `aucune`/`assistee`/`supervisee`/`autonome` (FR-007a) et d'appeler
      `llm_client.appeler_llm` avec une température de 0 pour la reproductibilité (research.md §3),
      puis parse la réponse en `ProfilAiAct` avec `echec=true` si la réponse est
      invalide/vide/inexploitable ou si la valeur d'autonomie ne fait pas partie des 4 valeurs
      attendues (FR-007, FR-007a, FR-008, FR-014, Edge Cases ; depends on T010, T017, T021, T033)
- [X] T036 [US1] Implémenter `src/services/rgpd_scanner.py` : fonction `scanner(selection:
      SelectionRgpd) -> list[DetectionRgpd]` appliquant les expressions régulières par catégorie
      (identité, contact, identifiant national, santé, biométrie, origine/croyances) et appelant
      immédiatement `rgpd_masking` pour produire `extrait_masque` (FR-010 ; depends on T011, T020,
      T033)
- [X] T037 [US1] Implémenter `src/services/report_builder.py` : fonction `combiner(mode_entree,
      depot, documentation, profil_aiact, detections_rgpd, non_conformites, appels_llm,
      tailles_envoyees, arborescence_tronquee: bool = False) -> ProfilProjetCombine` fusionnant
      les résultats en un profil unique, avec avertissements explicites (absence de détection
      RGPD, absence de fichier pertinent, source ignorée, "liste de fichiers du dépôt incomplète"
      si `arborescence_tronquee=true`) (FR-003a, FR-011, FR-012 ; depends on T013)
- [X] T038 [US1] Implémenter `src/services/report_builder.py::rendre_html(profil:
      ProfilProjetCombine) -> RapportFinal` produisant le HTML structuré à partir d'un template
      Jinja2, sans jamais introduire de champ de score/niveau de risque agrégé (FR-012, FR-014 ;
      depends on T037, T042 ; test T032a doit échouer avant cette tâche)
- [X] T039 [P] [US1] Créer le template Jinja2 `src/web/templates/formulaire.html` (formulaire
      `GET /` : `repo_url`, `documentation_texte`, `documentation_fichier`, bouton de soumission
      unique) (contracts/web-interface.md GET /)
- [X] T040 [P] [US1] Créer le template Jinja2 `src/web/templates/rapport.html` (sections : profil AI
      Act avec citations, détections RGPD avec extraits masqués, absence explicite si vide, nombre
      d'appels LLM et taille envoyée, bouton de téléchargement) (FR-012, FR-015, contracts/web-
      interface.md POST /evaluate succès complet)
- [X] T041 [P] [US1] Créer le template Jinja2 `src/web/templates/erreur.html` (message d'erreur clair
      réutilisable pour dépôt privé/inexistant, rate limit GitHub, documentation vide/illisible,
      aucune entrée exploitable) (contracts/web-interface.md, tableau des réponses d'erreur)
- [X] T042 [US1] Implémenter `src/web/app.py` : application FastAPI avec route `GET /` rendant
      `formulaire.html` (contracts/web-interface.md GET / ; depends on T039 ; tests T032 doit
      échouer avant cette tâche)
- [X] T043 [US1] Implémenter la route `POST /evaluate` dans `src/web/app.py` orchestrant le pipeline
      complet : `input_router.determiner_mode` → (mode dépôt: `github_client.verifier_accessibilite`
      + `lister_fichiers` + `file_selector` ; mode documentation: contenu direct, troncature à 40 000
      caractères si nécessaire) → `retriever.rechercher` → `aiact_analyzer.analyser` →
      `rgpd_scanner.scanner` → `report_builder.combiner` → `rendre_html`, avec gestion des cas
      d'erreur (dépôt privé/inexistant → message clair sans appel LLM ; rate limit GitHub distingué ;
      documentation vide/illisible/binaire rejetée) et affichage du rapport ou de l'erreur sur la
      même page (FR-001, FR-001a, FR-002, FR-002a, FR-006a, FR-016 ; depends on T018, T019, T033-T041
      ; tests T026-T031 doivent échouer avant cette tâche)

**Checkpoint**: User Story 1 fonctionnelle et testable indépendamment (rapport complet en mode dépôt
et en mode documentation).

---

## Phase 4: User Story 2 - Recevoir une liste de non-conformités justifiées par des références légales retrouvées (Priority: P1)

**Goal**: Le rapport inclut une liste de non-conformités potentielles, chacune rattachée à un
passage légal effectivement récupéré par le RAG pour cette évaluation.

**Independent Test**: Soumettre un dépôt/documentation avec une caractéristique connue de
non-conformité (ex. absence de base légale pour données de santé) → entrée de non-conformité avec
référence légale correspondant à un passage réellement récupéré (quickstart.md Scénario 3).

### Tests for User Story 2 (obligatoire — Principe II)

- [ ] T044 [P] [US2] Test unitaire cas conforme + cas non conforme pour la production de
      `NonConformite` à partir d'un `ProfilAiAct`/`DetectionRgpd` et d'une liste de
      `PassageLegalRecupere` : un aspect avec passage pertinent suffisant produit une
      `NonConformite.passage_source` référençant ce passage ; un aspect sans passage suffisamment
      pertinent NE produit PAS de `NonConformite` (dans
      `tests/unit/test_aiact_analyzer_nonconformites.py`) (FR-013, FR-019, data-model.md
      NonConformite invariant)
- [ ] T045 [P] [US2] Test d'intégration : dépôt/documentation avec caractéristique de non-conformité
      connue (absence de base légale pour données de santé, présente dans le corpus de test T014) →
      rapport contient une `NonConformite` dont `passage_source` correspond à un `id_reference`
      listé dans les `PassageLegalRecupere` réellement retournés pour cette évaluation, dans
      `tests/integration/test_evaluate_nonconformites.py` (Acceptance Scenarios US2.1–2, quickstart.md
      Scénario 3)
- [ ] T046 [P] [US2] Test d'intégration : évaluation sans caractéristique de non-conformité couverte
      par le corpus de test → rapport indique explicitement l'absence de point identifié, dans
      `tests/integration/test_evaluate_nonconformites.py` (Acceptance Scenario US2.3, quickstart.md
      Scénario 3 point 4)
- [ ] T047 [P] [US2] Test d'intégration : aspect détecté pour lequel aucun passage RAG suffisamment
      pertinent n'est récupéré → aspect non transformé en non-conformité inventée, rapport signale
      l'absence de référence disponible, dans `tests/integration/test_evaluate_nonconformites.py`
      (Acceptance Scenario US2.4)

### Implementation for User Story 2

- [ ] T048 [US2] Étendre `src/services/aiact_analyzer.py::analyser` pour que le prompt LLM demande
      également une liste de points de non-conformité potentiels, chacun rattaché explicitement à un
      `id_reference` parmi les `passages` fournis dans l'appel, et parser la réponse en
      `list[NonConformite]` (`origine="profil_aiact"`), en rejetant toute non-conformité dont le
      `passage_source` ne figure pas dans les passages effectivement transmis (FR-007, FR-013,
      FR-019 ; depends on T035 ; test T044 doit échouer avant cette tâche)
- [ ] T049 [US2] Étendre `src/services/rgpd_scanner.py` (ou ajouter une fonction dédiée dans
      `report_builder.py`) pour associer chaque `DetectionRgpd` pertinente à un passage RAG récupéré
      via `retriever.rechercher` sur le thème de la catégorie détectée, produisant des
      `NonConformite` supplémentaires (`origine="detection_rgpd"`) uniquement quand un passage
      suffisamment pertinent existe (FR-013, FR-019 ; depends on T017, T036)
- [ ] T050 [US2] Intégrer la fusion des `NonConformite` (profil AI Act + détections RGPD) dans
      `src/services/report_builder.py::combiner`, avec avertissement explicite "aucune non-conformité
      identifiée" si la liste est vide (FR-012, US2 Acceptance Scenario 3 ; depends on T037, T048,
      T049)
- [ ] T051 [US2] Mettre à jour `src/web/templates/rapport.html` pour afficher la section
      non-conformités (description en langage clair + référence légale, ou message d'absence
      explicite) (FR-012 ; depends on T040, T050)

**Checkpoint**: User Stories 1 ET 2 fonctionnelles indépendamment (rapport avec non-conformités
ancrées dans le RAG).

---

## Phase 5: User Story 3 - Respecter un budget d'appels LLM strict (Priority: P2)

**Goal**: Chaque évaluation respecte ≤2 appels LLM et ≤40 000 caractères par appel, le nombre
d'appels et la taille envoyée sont exposés.

**Independent Test**: Exécuter une évaluation sur un dépôt volumineux et vérifier via les
compteurs exposés qu'au maximum 2 appels LLM sont effectués et qu'aucun appel ne dépasse le plafond
(quickstart.md Scénario 4).

### Tests for User Story 3 (obligatoire — Principe II)

- [ ] T052 [P] [US3] Test unitaire cas conforme + cas non conforme pour le plafonnement à 40 000
      caractères dans `aiact_analyzer.py` : contenu source + passages RAG cumulés ≤40 000 → envoyé
      tel quel ; dépassement → contenu source tronqué en priorité (passages RAG conservés), dans
      `tests/unit/test_aiact_analyzer_budget.py` (FR-008, research.md §7 conséquence)
- [ ] T053 [P] [US3] Test unitaire cas conforme + cas non conforme pour le compteur
      `appels_llm_effectues` : un appel LLM réussi incrémente le compteur à 1 ; un dépôt volumineux
      (>15 fichiers pertinents par catégorie) ne déclenche jamais plus de 2 appels au total, dans
      `tests/unit/test_llm_budget.py` (FR-009)
- [ ] T054 [P] [US3] Test d'intégration : dépôt de plusieurs centaines de fichiers → sélections
      AI Act et RGPD bornées à 15 fichiers chacune avec `selection_partielle=true`, au maximum 2
      appels LLM comptabilisés, aucun appel >40 000 caractères, recherche RAG absente du compteur
      LLM, dans `tests/integration/test_evaluate_budget.py` (Acceptance Scenarios US3.1–4,
      quickstart.md Scénario 4, SC-002)

### Implementation for User Story 3

- [ ] T055 [US3] Implémenter le plafonnement de taille dans `src/services/aiact_analyzer.py` :
      fonction `construire_prompt(selection, passages) -> str` qui tronque en priorité le contenu
      source (fichiers ou documentation) pour respecter ≤40 000 caractères cumulés, en conservant les
      passages RAG (FR-008 ; depends on T035 ; test T052 doit échouer avant cette tâche)
- [ ] T056 [US3] Implémenter le comptage `appels_llm_effectues` et `taille_envoyee_par_appel` dans
      `src/services/llm_client.py::appeler_llm`, propagé jusqu'à `ProfilProjetCombine` via
      `report_builder.combiner` (FR-009, FR-015 ; depends on T021, T037 ; test T053 doit échouer
      avant cette tâche)
- [ ] T057 [US3] Mettre à jour `src/web/templates/rapport.html` pour afficher le nombre d'appels LLM
      effectués et la taille envoyée par appel (FR-015 ; depends on T040, T056)

**Checkpoint**: User Stories 1, 2 ET 3 fonctionnelles indépendamment (budget LLM vérifiable et
respecté).

---

## Phase 6: User Story 4 - Détecter les données personnelles sans appel LLM (Priority: P3)

**Goal**: La détection RGPD par motifs couvre les 6 catégories sans aucun appel LLM.

**Independent Test**: Fournir un contenu de test avec motifs connus (email, numéro de sécurité
sociale, identifiant de santé) et vérifier la détection correcte sans appel LLM (quickstart.md
Scénario 5).

### Tests for User Story 4 (obligatoire — Principe II, une paire conforme/non conforme par catégorie)

- [ ] T058 [P] [US4] Test unitaire cas conforme (motif email valide détecté) + cas non conforme
      (texte sans motif email → aucune détection) pour la catégorie `contact` dans
      `tests/unit/test_rgpd_scanner_contact.py` (FR-010, SC-005)
- [ ] T059 [P] [US4] Test unitaire cas conforme + cas non conforme pour la catégorie `identite`
      (ex. nom complet associé à un identifiant structuré) dans
      `tests/unit/test_rgpd_scanner_identite.py` (FR-010, SC-005)
- [ ] T060 [P] [US4] Test unitaire cas conforme + cas non conforme pour la catégorie
      `identifiant_national` (ex. numéro de sécurité sociale français) dans
      `tests/unit/test_rgpd_scanner_identifiant_national.py` (FR-010, SC-005)
- [ ] T061 [P] [US4] Test unitaire cas conforme + cas non conforme pour la catégorie `sante` (ex.
      mots-clés/colonnes de données de santé dans un schéma) dans
      `tests/unit/test_rgpd_scanner_sante.py` (FR-010, SC-005)
- [ ] T062 [P] [US4] Test unitaire cas conforme + cas non conforme pour la catégorie `biometrie`
      (ex. colonnes/motifs d'empreinte, reconnaissance faciale) dans
      `tests/unit/test_rgpd_scanner_biometrie.py` (FR-010, SC-005)
- [ ] T063 [P] [US4] Test unitaire cas conforme + cas non conforme pour la catégorie
      `origine_croyances` (ex. mots-clés d'origine ethnique/religion dans des fixtures) dans
      `tests/unit/test_rgpd_scanner_origine_croyances.py` (FR-010, SC-005)
- [ ] T064 [P] [US4] Test unitaire vérifiant qu'aucune valeur brute complète n'apparaît dans
      `DetectionRgpd.extrait_masque` pour chacune des 6 catégories (assertion que la valeur d'entrée
      connue n'est jamais une sous-chaîne exacte du masque produit) dans
      `tests/unit/test_rgpd_masking.py` (FR-010a)
- [ ] T065 [P] [US4] Test d'intégration : contenu de test avec motifs connus des 3 catégories
      (email, numéro de sécurité sociale, identifiant de santé) et contenu sans motif → détections
      correctes avec extrait masqué et source, compteur `appels_llm_effectues` inchangé par cette
      étape, dans `tests/integration/test_evaluate_rgpd_scan.py` (Acceptance Scenarios US4.1–2,
      quickstart.md Scénario 5)

### Implementation for User Story 4

- [ ] T066 [US4] Implémenter dans `src/services/rgpd_scanner.py` les expressions régulières pour les
      6 catégories (`identite`, `contact`, `identifiant_national`, `sante`, `biometrie`,
      `origine_croyances`), une constante nommée par catégorie pour l'audit (`DetectionRgpd.motif`)
      (FR-010, research.md §4 ; depends on T036 déjà créé en Phase 3 — ici on complète la couverture
      des 6 catégories ; tests T058-T064 doivent échouer avant cette tâche)
- [ ] T067 [US4] Compléter `src/services/rgpd_masking.py` avec une fonction de masquage dédiée par
      catégorie (pas seulement email/numéro national) garantissant qu'aucune valeur brute complète
      n'est retournée pour les 6 catégories (FR-010a ; depends on T020 ; test T064 doit échouer avant
      cette tâche)

**Checkpoint**: User Stories 1 à 4 fonctionnelles indépendamment (détection RGPD complète, sans LLM,
sur les 6 catégories).

---

## Phase 7: User Story 5 - Télécharger le rapport généré (Priority: P3)

**Goal**: L'utilisateur peut télécharger le rapport affiché, sans persistance serveur.

**Independent Test**: Générer un rapport, déclencher le téléchargement, vérifier que le fichier
contient l'intégralité du rapport et qu'aucune trace ne subsiste côté serveur (quickstart.md
Scénario 6).

### Tests for User Story 5 (obligatoire — Principe II)

- [ ] T068 [P] [US5] Test contractuel : après un `POST /evaluate` réussi, le téléchargement (bouton/
      requête du même cycle) retourne 200 avec en-tête `Content-Disposition: attachment` et un corps
      identique au rapport affiché, dans `tests/contract/test_evaluate_download.py`
      (contracts/web-interface.md GET /evaluate/download, FR-001b)
- [ ] T069 [P] [US5] Test d'intégration cas conforme + cas non conforme : téléchargement immédiat
      après génération → fichier complet obtenu ; absence de toute écriture disque/DB détectable
      après la réponse (assertion qu'aucun fichier n'est créé sous un répertoire de données
      temporaire surveillé par le test) dans `tests/integration/test_evaluate_download.py`
      (Acceptance Scenarios US5.1–2, quickstart.md Scénario 6, SC-009)

### Implementation for User Story 5

- [ ] T070 [US5] Implémenter le téléchargement dans `src/web/app.py` : le même rendu HTML produit par
      `POST /evaluate` (T043) est proposé en pièce jointe dans la même réponse (double contenu ou
      second bouton de soumission renvoyant le rapport en `Content-Disposition: attachment`), sans
      écriture serveur intermédiaire (FR-001b, FR-017, contracts/web-interface.md GET /evaluate/
      download ; depends on T038, T043 ; test T068 doit échouer avant cette tâche)
- [ ] T071 [US5] Ajouter le bouton/lien de téléchargement dans `src/web/templates/rapport.html`
      pointant vers la route de téléchargement (FR-001b ; depends on T040, T070)

**Checkpoint**: Toutes les user stories (US1–US5) fonctionnelles indépendamment.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Améliorations transverses après complétion des user stories prioritaires

- [ ] T072 [P] Test contractuel : dépôt privé/inexistant → message d'erreur clair distinguant ce cas,
      0 appel LLM, dans `tests/contract/test_evaluate_errors.py` (FR-002, SC-006, Edge Cases)
- [ ] T073 [P] Test contractuel : limitation de débit GitHub (403/429) → message distinguant cette
      cause d'un dépôt invalide, dans `tests/contract/test_evaluate_errors.py` (Edge Cases,
      research.md §2)
- [ ] T074 [P] Test contractuel : réponse LLM invalide/vide → rapport produit quand même avec
      `ProfilAiAct.echec=true` et détections RGPD présentes, dans
      `tests/contract/test_evaluate_errors.py` (contracts/web-interface.md, Edge Cases)
- [ ] T075 [P] Test unitaire : fichier téléversé non-texte (binaire) → rejeté avant tout appel LLM,
      dans `tests/unit/test_documentation_validation.py` (Edge Cases FR-016)
- [ ] T076 [P] Documentation : mettre à jour `README.md` à la racine avec les instructions de
      lancement issues de `quickstart.md` (construction de l'index RAG, variable
      `ANTHROPIC_API_KEY`, `uvicorn src.web.app:app --reload`)
- [ ] T077 Exécuter manuellement les 6 scénarios de `quickstart.md` de bout en bout (dépôt réel
      public, documentation collée, non-conformité connue, dépôt volumineux, motifs RGPD,
      téléchargement) et consigner les résultats, pour valider SC-001 à SC-009
- [ ] T078 Vérifier que `SC-001` (rapport complet en <3 minutes pour un dépôt <1000 fichiers) est
      respecté en mesurant la durée du scénario 1 de quickstart.md sur un dépôt réel de taille
      représentative
- [ ] T079 [P] Créer un `Dockerfile` à la racine (image `python:3.11-slim`, installe
      `requirements.txt`, copie `src/`, expose le port `8000` et lance
      `uvicorn src.web.app:app --host 0.0.0.0 --port 8000`), pour un déploiement conteneurisé sur
      Azure App Service (Web App for Containers) plutôt que sur une plateforme serverless
      incompatible avec le budget de temps (<3 min, SC-001) et la taille du modèle d'embedding local
      (research.md §7)
- [ ] T080 Provisionner les ressources Azure (via le portail ou `az cli`, sur l'abonnement crédits
      étudiants) : un groupe de ressources, un plan App Service Linux (tier `B1` minimum pour
      supporter le modèle d'embedding local — le tier gratuit `F1` est trop limité en mémoire/CPU),
      et une Web App en mode conteneur personnalisé (`az webapp create --deployment-container-image-name`) ;
      définir l'application setting `WEBSITES_PORT=8000` pour qu'Azure route le trafic vers le port
      exposé par le `Dockerfile` ; dépend de T079 (depends on T079)
- [ ] T081 Documenter dans `README.md` la configuration du secret `ANTHROPIC_API_KEY` via
      Configuration → Application settings de la Web App Azure (jamais committé en clair), ainsi que
      le comportement du tier choisi (pas de mise en veille sur `B1` avec "Always On" activé,
      contrairement à un tier gratuit/serverless) (depends on T080)
- [ ] T082 Déployer l'image (build de l'image Docker, push vers Azure Container Registry ou
      déploiement direct via `az webapp up`/`az webapp config container set`, vérifier que le build
      et le démarrage du conteneur passent) et valider que l'URL publique
      `https://<app-name>.azurewebsites.net` sert le formulaire `GET /` en HTTPS sans authentification
      requise pour un visiteur externe (depends on T081)
- [ ] T083 Configurer le déploiement continu vers Azure App Service depuis le dépôt GitHub : créer
      un principal de service Azure (`az ad sp create-for-rbac` ou profil de publication téléchargé
      depuis le portail Azure), l'ajouter comme secret GitHub Actions (`AZURE_WEBAPP_PUBLISH_PROFILE`
      ou `AZURE_CREDENTIALS`), et ajouter le workflow `.github/workflows/deploy-azure.yml` qui, à
      chaque push sur `main`, construit l'image Docker et la déploie sur la Web App via l'action
      `azure/webapps-deploy@v3` (ou `az webapp deploy`) ; vérifier qu'un push déclenche bien une
      reconstruction et un redéploiement automatiques (depends on T082)
- [ ] T084 Vérifier `SC-004` (coût LLM cumulé sous 10€ sur 100 évaluations) : exécuter le scénario
      1 ou 2 de `quickstart.md` un nombre représentatif de fois, sommer le champ
      `taille_envoyee_par_appel` exposé (FR-015) à travers ces exécutions, appliquer le tarif du
      modèle Haiku (research.md §3) pour projeter le coût sur 100 évaluations, et consigner le
      résultat (quickstart.md "Vérification du budget global (SC-004)" ; depends on T077)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Aucune dépendance — peut démarrer immédiatement
- **Foundational (Phase 2)**: Dépend de Setup — BLOQUE toutes les user stories
- **User Stories (Phase 3+)**: Dépendent toutes de Foundational
  - US1 (P1, Phase 3) : peut démarrer dès Foundational terminé
  - US2 (P1, Phase 4) : dépend de US1 (`aiact_analyzer.py`, `rgpd_scanner.py`, `report_builder.py`
    créés en Phase 3) — non indépendante en implémentation malgré sa priorité P1, car elle étend les
    mêmes services ; reste indépendamment testable une fois codée
  - US3 (P2, Phase 5) : dépend de US1 (`aiact_analyzer.py`, `llm_client.py`) — étend le même appel LLM
  - US4 (P3, Phase 6) : dépend de US1 (`rgpd_scanner.py` créé en Phase 3, complété ici pour les 6
    catégories) — indépendamment testable
  - US5 (P3, Phase 7) : dépend de US1 (`report_builder.py::rendre_html`, route `POST /evaluate`)
- **Polish (Phase 8)**: Dépend de toutes les user stories désirées étant complètes

### User Story Dependencies

- **US1 (P1)**: Fondation de toutes les autres stories — aucune dépendance vers une autre story
- **US2 (P1)**: Étend `aiact_analyzer.py`/`rgpd_scanner.py`/`report_builder.py` de US1
- **US3 (P2)**: Étend `aiact_analyzer.py`/`llm_client.py` de US1
- **US4 (P3)**: Étend `rgpd_scanner.py`/`rgpd_masking.py` de US1 (couverture des 6 catégories)
- **US5 (P3)**: Étend `report_builder.py`/route `POST /evaluate` de US1

### Within Each User Story

- Tests écrits et DOIVENT échouer avant l'implémentation (Principe II, non négociable)
- Modèles (Phase 2) avant services
- Services avant templates/routes
- Story complète avant de passer à la story suivante (ordre de priorité recommandé : US1 → US2 → US3
  → US4 → US5)

### Parallel Opportunities

- Toutes les tâches Setup marquées [P] (T003-T004) en parallèle
- Toutes les tâches Foundational marquées [P] (T005-T012, T017-T021) en parallèle, après T001-T002 ;
  T013-T016 séquentielles (dépendent des modèles / les uns des autres)
- Toutes les tests [P] d'une même story en parallèle (fichiers différents)
- US2, US3, US4, US5 peuvent être développées en parallèle par des personnes différentes une fois
  US1 (Phase 3) terminée, chacune touchant des fichiers/fonctions majoritairement distincts (avec
  attention aux fichiers partagés `aiact_analyzer.py`, `rgpd_scanner.py`, `report_builder.py`,
  `rapport.html` en cas de travail simultané)

---

## Parallel Example: Foundational Phase

```bash
# Lancer les modèles de domaine indépendants ensemble (après T001-T002) :
Task: "Définir DepotCible et ModeEntree dans src/models/depot.py"
Task: "Définir DocumentationFournie dans src/models/documentation.py"
Task: "Définir FichierDepot et FichierAvecContenu dans src/models/fichier.py"
Task: "Définir SelectionAiAct et SelectionRgpd dans src/models/selection.py"
Task: "Définir PassageLegalRecupere et CorpusJuridique dans src/models/legal_corpus.py"
Task: "Définir ProfilAiAct dans src/models/profil_aiact.py"
Task: "Définir DetectionRgpd dans src/models/detection_rgpd.py"
Task: "Définir NonConformite dans src/models/non_conformite.py"
```

## Parallel Example: User Story 1 Tests

```bash
Task: "Test unitaire determiner_mode dans tests/unit/test_input_router.py"
Task: "Test unitaire sélection AI Act dans tests/unit/test_file_selector.py"
Task: "Test unitaire sélection RGPD dans tests/unit/test_file_selector.py"
Task: "Test unitaire retriever RAG dans tests/unit/test_retriever.py"
Task: "Test intégration mode dépôt dans tests/integration/test_evaluate_repo_mode.py"
Task: "Test intégration mode documentation dans tests/integration/test_evaluate_documentation_mode.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 seule)

1. Compléter Phase 1: Setup
2. Compléter Phase 2: Foundational (CRITIQUE — bloque toutes les stories)
3. Compléter Phase 3: User Story 1 (rapport complet, mode dépôt et documentation)
4. **STOP et VALIDER**: Tester US1 indépendamment via quickstart.md Scénarios 1–2
5. Démo si prêt — c'est déjà un produit utilisable (rapport AI Act + RGPD affiché)

### Incremental Delivery

1. Setup + Foundational → Fondation prête
2. US1 → Test indépendant → Démo (MVP, rapport complet)
3. US2 → Test indépendant → Démo (non-conformités ancrées dans le RAG)
4. US3 → Test indépendant → Démo (budget LLM vérifiable)
5. US4 → Test indépendant → Démo (couverture complète des 6 catégories RGPD)
6. US5 → Test indépendant → Démo (téléchargement)
7. Polish (Phase 8) → Validation finale des Success Criteria

### Parallel Team Strategy

Avec plusieurs développeurs :

1. L'équipe complète Setup + Foundational ensemble
2. Un développeur complète US1 (bloquante pour les autres)
3. Une fois US1 terminée :
   - Développeur A : US2 (non-conformités)
   - Développeur B : US3 (budget LLM)
   - Développeur C : US4 (couverture RGPD complète) et US5 (téléchargement)
4. Les stories s'intègrent dans `report_builder.py`/`rapport.html`/`app.py` partagés — coordonner
   les modifications de ces fichiers

---

## Notes

- [P] = fichiers différents, pas de dépendance bloquante
- Chaque tâche de test DOIT échouer avant l'implémentation correspondante (Principe II, non
  négociable pour ce projet — pas d'option "tests optionnels" ici)
- [Story] mappe chaque tâche à une user story pour la traçabilité
- Committer après chaque tâche ou groupe logique
- S'arrêter à chaque checkpoint pour valider la story indépendamment
- Éviter : tâches vagues, conflits sur un même fichier, dépendances cross-story qui casseraient
  l'indépendance de test de chaque story
- Tâches `Txxxa` (T004a, T032a) : ajoutées après la revue `/speckit-analyze` du 2026-09-16 pour
  combler des trous de couverture (CI, test négatif FR-014) sans renuméroter l'ensemble du
  fichier ; elles suivent la même règle d'exécution que leur voisine numérique (T004a avant la fin
  de Setup, T032a avant T035, Principe II)
