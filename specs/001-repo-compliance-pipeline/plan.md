# Implementation Plan: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Branch**: `001-repo-compliance-pipeline` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-repo-compliance-pipeline/spec.md` (amendée le
2026-09-16 : second mode d'entrée par documentation, RAG pour les citations légales, liste de
non-conformités dans le scope, rapport téléchargeable)

## Summary

Un utilisateur soumet, via un formulaire web, soit l'URL d'un dépôt GitHub public, soit de la
documentation de projet fournie directement (texte collé ou fichier). En mode dépôt, le système
vérifie l'accessibilité, liste les fichiers via l'API GitHub non authentifiée, puis sélectionne
deux sous-ensembles bornés et déterministes (≤15 fichiers pour l'AI Act, ≤15 pour le RGPD) ; en
mode documentation, le contenu fourni est utilisé directement comme source unique. Un composant de
recherche légale (RAG) — index vectoriel local du corpus AI Act/RGPD, construit une fois hors
ligne avec un modèle d'embedding open-source exécuté localement — récupère, pour chaque
évaluation, les passages légaux les plus pertinents (recherche sans aucun appel LLM payant). Le
contenu source AI Act et ces passages récupérés sont envoyés à un LLM (1 appel max, ≤40 000
caractères) pour déduire secteur d'activité / finalité / autonomie décisionnelle et produire une
liste de points de non-conformité potentiels, chacun rattaché à un passage récupéré. En parallèle,
le contenu pertinent RGPD est scanné par expressions régulières déterministes (0 appel LLM) pour
détecter 6 catégories de données personnelles, chacune reportée avec un extrait masqué. Les
résultats sont fusionnés en un profil de projet combiné, rendus en une page HTML de rapport
(langage clair), affichée dans le navigateur et téléchargeable par l'utilisateur, sans persistance
côté serveur.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (formulaire web + rendu HTML server-side via Jinja2), httpx
(appels API GitHub et LLM), Anthropic Claude API (modèle Haiku, pour le seul appel LLM payant
d'inférence AI Act + non-conformités), `sentence-transformers` (modèle d'embedding open-source,
exécuté localement, pour l'indexation hors ligne du corpus juridique et l'encodage de la requête à
chaque évaluation — aucun appel API payant), `numpy` (recherche par similarité cosinus en mémoire
sur les vecteurs pré-calculés — pas de base vectorielle externe), `re` (bibliothèque standard) pour
la détection RGPD par motifs

**Storage**: N/A pour les données de requête — aucune persistance (FR-017), tout l'état d'une
évaluation vit dans la durée d'une requête HTTP. Seule donnée versionnée statique : l'index
vectoriel pré-calculé du corpus juridique (fichier(s) plat(s), ex. `.npy`/`.json`, généré une fois
par un script hors ligne et committé avec le corpus — pas une base de données)

**Testing**: pytest (unitaire + intégration), avec cassettes HTTP enregistrées (ex. `respx`) pour
simuler l'API GitHub et l'API LLM sans appels réseau réels en CI ; le composant RAG est testé avec
l'index pré-calculé versionné (pas de réentraînement/téléchargement de modèle en CI si évitable —
cf. research.md)

**Target Platform**: Service web Linux (conteneurisé), accessible via navigateur

**Project Type**: Application web à projet unique (backend FastAPI qui sert aussi les pages HTML
— pas de frontend séparé, cohérent avec le Principe V de simplicité)

**Performance Goals**: Rapport complet en < 3 minutes pour un dépôt de moins de 1000 fichiers
(SC-001)

**Constraints**: ≤2 appels LLM payants par évaluation (FR-009) ; ≤40 000 caractères par appel LLM
(FR-008, contenu source + passages RAG cumulés) ; ≤15 fichiers sélectionnés par catégorie en mode
dépôt (FR-006) ; 0 appel LLM pour la détection RGPD (FR-010) ; 0 appel LLM payant pour
l'indexation/la recherche légale (FR-018, embedding local uniquement) ; aucune citation hors des
passages effectivement récupérés pour l'évaluation (FR-013, FR-019) ; 0 persistance du rapport, du
contenu analysé et des extraits détectés (FR-017) ; budget cumulé de 10€ sur 100 évaluations
(SC-004)

**Scale/Scope**: Une évaluation traite une seule source (dépôt ou documentation) à la fois et
produit un seul rapport HTML, téléchargeable ; usage attendu : projet étudiant, trafic faible, pas
de montée en charge horizontale visée à ce stade

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Legal Fidelity & Traceability** — PASS. FR-013/FR-019 renforcent l'exigence par rapport à
  la version précédente : chaque citation (profil AI Act et, désormais, liste de non-conformités)
  doit correspondre à un passage **effectivement récupéré par le RAG pour cette évaluation
  précise**, pas seulement "présent quelque part dans le corpus". Le corpus lui-même (Key Entity
  "Corpus juridique de référence") reste une ressource fournie séparément, modélisée comme données
  statiques versionnées, désormais indexées pour la recherche.
- **II. Test-First Verification (NON-NEGOTIABLE)** — PASS avec obligation de conception élargie :
  aux règles de détection RGPD (FR-010) et de sélection de fichiers (FR-006) s'ajoute la règle de
  récupération RAG (FR-018/019 : un profil connu doit récupérer un ensemble déterministe de
  passages pour un index figé) et la règle de détermination du mode d'entrée (FR-001, dépôt vs
  documentation). Chacune devra avoir un cas conforme et un cas non conforme testés avant d'être
  considérée terminée (reflété dans tasks.md, hors scope de ce plan).
- **III. Auditability & Explainability** — PASS. FR-015 (exposition du nombre d'appels LLM et de
  la taille envoyée) et FR-006 (sélection déterministe) restent inchangés. Nouveauté : chaque point
  de non-conformité et chaque élément du profil AI Act doit pouvoir être retracé jusqu'au passage
  RAG précis qui l'a justifié (voir data-model.md, `PassageLegalRecupere`), renforçant
  l'explicabilité plutôt que de l'affaiblir.
- **IV. Privacy-by-Design (Self-Application)** — PASS. FR-017 (non-persistance) et FR-010a
  (extraits masqués) inchangés. Le mode documentation (texte collé/fichier) suit la même règle de
  non-persistance dès son ingestion. Le téléchargement du rapport (FR-001b) est généré à la volée
  dans la réponse HTTP, sans écriture serveur intermédiaire — aucun nouveau point de persistance
  introduit.
- **V. Simplicity & Maintainability** — PASS avec vigilance documentée : l'ajout d'un composant RAG
  (modèle d'embedding local + recherche vectorielle) est une complexité nouvelle par rapport à la
  V1. Elle est justifiée par un besoin fonctionnel concret et explicite du commanditaire (RAG
  demandé, non spéculatif), et bornée : indexation **hors ligne, une seule fois** (pas de
  réentraînement par évaluation), recherche en mémoire via `numpy`/similarité cosinus plutôt qu'une
  base vectorielle externe à héberger — pas de nouvelle infrastructure à maintenir en production.
  Toujours un seul service web, pas de base de données, pas de file d'attente.

Aucune violation nécessitant la section Complexity Tracking (la complexité RAG est justifiée
ci-dessus et bornée techniquement).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/          # Entités du domaine (data-model.md) : DepotCible, DocumentationFournie,
│                    # ModeEntree, FichierDepot, FichierAvecContenu, SelectionAiAct, SelectionRgpd,
│                    # PassageLegalRecupere, ProfilAiAct, DetectionRgpd, NonConformite,
│                    # ProfilProjetCombine, CorpusJuridique, RapportFinal
├── services/
│   ├── input_router.py      # Détermine le mode d'entrée (dépôt vs documentation) (FR-001)
│   ├── github_client.py     # Liste des fichiers via l'API GitHub non authentifiée (FR-002/003)
│   ├── file_selector.py     # Sélection bornée + règle de priorité déterministe (FR-004/005/006)
│   ├── legal_rag/
│   │   ├── build_index.py   # Script hors ligne : encode le corpus avec le modèle d'embedding
│   │   │                    # local, produit l'index vectoriel versionné (exécuté une fois,
│   │   │                    # jamais à l'exécution d'une évaluation) (FR-018)
│   │   └── retriever.py     # Encode la requête (profil/texte source) avec le même modèle local
│   │                        # et interroge l'index (similarité cosinus, numpy) — 0 appel LLM
│   │                        # payant (FR-018/019)
│   ├── aiact_analyzer.py    # Construction du prompt (contenu source + passages RAG) + appel LLM
│   │                        # unique produisant profil AI Act + liste de non-conformités
│   │                        # (FR-007/008/019)
│   ├── rgpd_scanner.py      # Détection par motifs, sans LLM (FR-010/010a)
│   ├── legal_corpus.py      # Accès en lecture seule au corpus juridique de référence (FR-013)
│   └── report_builder.py    # Fusion en profil combiné + rendu HTML + export téléchargeable
│                             # (FR-011/012/001b)
├── web/
│   ├── app.py                # Application FastAPI (formulaire à 2 modes d'entrée, affichage du
│   │                          # rapport, route de téléchargement)
│   └── templates/             # Templates Jinja2 du formulaire et du rapport HTML
└── data/
    └── legal_corpus/          # Corpus juridique de référence (textes statiques versionnés) +
                                # index vectoriel pré-calculé (généré par build_index.py)

tests/
├── contract/         # Tests du contrat web (routes FastAPI, voir contracts/)
├── integration/      # Parcours de bout en bout avec API GitHub/LLM simulées, modes dépôt et
│                     # documentation, téléchargement du rapport
└── unit/             # Règles de sélection de fichiers, détection RGPD, récupération RAG (cas
                       # conforme + non conforme par catégorie, requis par le Principe II)
```

**Structure Decision**: Projet unique (Option 1) — un seul service FastAPI qui sert le
formulaire (2 modes d'entrée), orchestre le pipeline (services/) — y compris le composant RAG en
sous-module `services/legal_rag/` — et rend le rapport HTML server-side (web/templates), affiché
et téléchargeable, sans frontend séparé (Principe V). Le corpus juridique et son index vectoriel
sont versionnés en tant que données statiques (`src/data/legal_corpus/`) plutôt qu'en base de
données ou service vectoriel externe, puisque l'indexation est un processus hors ligne exécuté une
fois (research.md) et que le système reste en lecture seule dessus à l'exécution (FR-013/018).

## Constitution Check (post-Phase 1 re-evaluation)

*Re-checked after data-model.md, contracts/, and quickstart.md were produced.*

- **I. Legal Fidelity & Traceability** — PASS confirmé. `data-model.md` fixe l'invariant que
  `RapportFinal.citations` et `NonConformite.passage_source` ne peuvent référencer qu'un
  `PassageLegalRecupere` effectivement retourné par le retriever pour l'évaluation en cours
  (FR-013/019) ; `contracts/web-interface.md` liste ce point comme invariant observable du contrat.
- **II. Test-First Verification** — PASS confirmé, avec obligation explicite reportée dans
  `quickstart.md` : chaque règle (sélection de fichiers, détermination du mode d'entrée, chacune
  des 6 catégories RGPD, récupération RAG sur un index figé) doit avoir un cas conforme et un cas
  non conforme dans `tests/unit/` avant d'être considérée terminée ; concrétisé en tâches par
  `/speckit-tasks`.
- **III. Auditability & Explainability** — PASS confirmé. `ProfilProjetCombine` expose
  `appels_llm_effectues` et `taille_envoyee_par_appel` (FR-015) ; `DetectionRgpd.motif` et
  `NonConformite.passage_source` conservent respectivement la règle et le passage ayant déclenché
  chaque élément du rapport, pour audit.
- **IV. Privacy-by-Design (Self-Application)** — PASS confirmé. `data-model.md` impose que
  `extrait_masque` (jamais la valeur complète) soit calculé au point de détection, avant toute
  autre étape du pipeline. Aucune entité n'a de champ de persistance ; le contrat web confirme
  qu'aucune écriture serveur n'a lieu (FR-017), y compris pour la génération du fichier téléchargé
  (FR-001b, généré dans la réponse HTTP).
- **V. Simplicity & Maintainability** — PASS confirmé. Un seul contrat web (`web-interface.md`,
  trois routes), aucune base de données, aucun service vectoriel externe hébergé — l'index RAG est
  un artefact statique versionné, construit hors ligne une seule fois.

Aucune violation : la section Complexity Tracking reste vide (la complexité RAG est justifiée dans
la Constitution Check ci-dessus, avec bornes techniques explicites).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Aucune violation identifiée — section non applicable.*
