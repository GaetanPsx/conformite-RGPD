# Implementation Plan: Pipeline d'extraction et d'analyse de conformité de dépôt GitHub

**Branch**: `001-repo-compliance-pipeline` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-repo-compliance-pipeline/spec.md`

## Summary

Un utilisateur soumet, via un formulaire web, l'URL d'un dépôt GitHub public. Le système
vérifie l'accessibilité du dépôt, liste ses fichiers via l'API GitHub non authentifiée, en
sélectionne deux sous-ensembles bornés et déterministes (≤15 fichiers pour l'AI Act, ≤15 pour le
RGPD), envoie la sélection AI Act à un LLM (1 appel max, ≤40 000 caractères) pour déduire secteur
d'activité / finalité / autonomie décisionnelle, et scanne la sélection RGPD par expressions
régulières déterministes (0 appel LLM) pour détecter 6 catégories de données personnelles,
chacune reportée avec un extrait masqué. Les deux résultats sont fusionnés en un profil de
projet combiné, puis rendus en une page HTML de rapport (langage clair, citations légales issues
d'un corpus de référence fermé), affichée directement dans le navigateur sans persistance côté
serveur.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (formulaire web + rendu HTML server-side via Jinja2), httpx
(appels API GitHub et LLM), Anthropic Claude API (modèle Haiku, pour le coût) pour le seul appel
LLM d'inférence AI Act, `re` (bibliothèque standard) pour la détection RGPD par motifs

**Storage**: N/A — aucune persistance (FR-017) ; tout l'état vit dans la durée d'une requête HTTP

**Testing**: pytest (unitaire + intégration), avec cassettes HTTP enregistrées (ex. `respx`) pour
simuler l'API GitHub et l'API LLM sans appels réseau réels en CI

**Target Platform**: Service web Linux (conteneurisé), accessible via navigateur

**Project Type**: Application web à projet unique (backend FastAPI qui sert aussi les pages HTML
— pas de frontend séparé, cohérent avec le Principe V de simplicité)

**Performance Goals**: Rapport complet en < 3 minutes pour un dépôt de moins de 1000 fichiers
(SC-001)

**Constraints**: ≤2 appels LLM par évaluation (FR-009) ; ≤40 000 caractères par appel LLM (FR-008)
; ≤15 fichiers sélectionnés par catégorie (FR-006) ; 0 appel LLM pour la détection RGPD (FR-010) ;
0 persistance du rapport, du contenu analysé et des extraits détectés (FR-017) ; budget cumulé de
10€ sur 100 évaluations (SC-004)

**Scale/Scope**: Une évaluation traite un seul dépôt à la fois et produit un seul rapport HTML ;
usage attendu : projet étudiant, trafic faible, pas de montée en charge horizontale visée à ce
stade

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Legal Fidelity & Traceability** — PASS. FR-013 interdit toute citation légale hors du
  corpus de référence fermé ; le corpus lui-même (Key Entity "Corpus juridique de référence") est
  une ressource fournie séparément (Assumptions), donc modélisable comme données statiques
  versionnées dans le dépôt. Aucune violation : chaque citation du rapport devra être résolue
  contre ce corpus avant affichage.
- **II. Test-First Verification (NON-NEGOTIABLE)** — PASS avec obligation de conception : les
  règles de détection RGPD (FR-010, 6 catégories) et les règles de sélection de fichiers (FR-006)
  sont des "règles" au sens de la constitution et devront chacune avoir un cas conforme et un cas
  non conforme testés avant d'être considérées terminées. Ceci sera reflété dans tasks.md (hors
  scope de ce plan).
- **III. Auditability & Explainability** — PASS. FR-015 (exposition du nombre d'appels LLM et de
  la taille envoyée) et FR-006 (règle de sélection entièrement déterministe, précisée en
  clarification : profondeur puis alphabétique) rendent le pipeline reproductible. Le rapport HTML
  doit néanmoins associer à chaque citation légale sa source dans le corpus (voir data-model.md)
  pour rester explicable à un lecteur non technique.
- **IV. Privacy-by-Design (Self-Application)** — PASS. FR-017 (non-persistance) et FR-010a
  (extraits masqués, jamais la valeur complète) implémentent directement la minimisation et la
  limitation de conservation exigées. Point de vigilance retenu pour la conception : les logs
  d'application (FR-015, FR-016) ne doivent pas eux-mêmes journaliser le contenu complet des
  fichiers analysés ni les valeurs détectées non masquées — à documenter dans data-model.md /
  quickstart.md.
- **V. Simplicity & Maintainability** — PASS. Un seul service web (FastAPI + Jinja2), pas de base
  de données, pas de file d'attente, pas de frontend séparé : la structure la plus simple
  satisfaisant les exigences fonctionnelles et le principe de non-persistance.

Aucune violation nécessitant la section Complexity Tracking.

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
├── models/          # Entités du domaine (data-model.md) : DepotCible, FichierDepot,
│                    # SelectionAiAct, SelectionRgpd, ProfilAiAct, DetectionRgpd,
│                    # ProfilProjetCombine, CorpusJuridique, RapportFinal
├── services/
│   ├── github_client.py     # Liste des fichiers via l'API GitHub non authentifiée (FR-002/003)
│   ├── file_selector.py     # Sélection bornée + règle de priorité déterministe (FR-004/005/006)
│   ├── aiact_analyzer.py    # Construction du prompt + appel LLM unique (FR-007/008)
│   ├── rgpd_scanner.py      # Détection par motifs, sans LLM (FR-010/010a)
│   ├── legal_corpus.py      # Accès en lecture seule au corpus juridique de référence (FR-013)
│   └── report_builder.py    # Fusion en profil combiné + rendu HTML (FR-011/012)
├── web/
│   ├── app.py                # Application FastAPI (formulaire + affichage du rapport)
│   └── templates/             # Templates Jinja2 du formulaire et du rapport HTML
└── data/
    └── legal_corpus/          # Corpus juridique de référence (fichiers statiques versionnés)

tests/
├── contract/         # Tests du contrat web (routes FastAPI, voir contracts/)
├── integration/      # Parcours de bout en bout avec API GitHub/LLM simulées
└── unit/             # Règles de sélection de fichiers et de détection RGPD (cas conforme +
                       # non conforme par catégorie, requis par le Principe II)
```

**Structure Decision**: Projet unique (Option 1) — un seul service FastAPI qui sert le
formulaire, orchestre le pipeline (services/) et rend le rapport HTML server-side (web/templates)
sans frontend séparé, conformément au Principe V (Simplicité). Le corpus juridique est versionné
en tant que données statiques (`src/data/legal_corpus/`) plutôt qu'en base de données, puisque le
système est en lecture seule dessus (FR-013) et qu'aucune autre persistance n'est requise
(FR-017).

## Constitution Check (post-Phase 1 re-evaluation)

*Re-checked after data-model.md, contracts/, and quickstart.md were produced.*

- **I. Legal Fidelity & Traceability** — PASS confirmé. `data-model.md` fixe l'invariant que
  `RapportFinal.citations` ne peut référencer que des `CorpusJuridique.id_reference` existants
  (FR-013), et `contracts/web-interface.md` liste ce point comme invariant observable du contrat.
- **II. Test-First Verification** — PASS confirmé, avec obligation explicite reportée dans
  `quickstart.md` : chaque règle (sélection de fichiers, chacune des 6 catégories RGPD) doit avoir
  un cas conforme et un cas non conforme dans `tests/unit/` avant d'être considérée terminée ;
  concrétisé en tâches par `/speckit-tasks`.
- **III. Auditability & Explainability** — PASS confirmé. `ProfilProjetCombine` expose
  `appels_llm_effectues` et `taille_envoyee_par_appel` (FR-015) ; `DetectionRgpd.motif` conserve
  la règle ayant déclenché chaque détection pour audit.
- **IV. Privacy-by-Design (Self-Application)** — PASS confirmé. `data-model.md` impose que
  `extrait_masque` (jamais la valeur complète) soit calculé au point de détection, avant toute
  autre étape du pipeline — aucune structure en aval ne transporte de valeur brute. Aucune entité
  n'a de champ de persistance ; le contrat web confirme qu'aucune écriture serveur n'a lieu
  (FR-017).
- **V. Simplicity & Maintainability** — PASS confirmé. Un seul contrat (`web-interface.md`, deux
  routes), aucune base de données, corpus juridique en données statiques versionnées plutôt qu'en
  service séparé.

Aucune violation : la section Complexity Tracking reste vide.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Aucune violation identifiée — section non applicable.*
