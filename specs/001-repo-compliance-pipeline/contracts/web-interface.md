# Contract: Interface web

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

Le système expose une surface d'interaction web server-rendered (FastAPI + Jinja2, cf.
research.md §1). Pas d'API JSON publique en V1 (hors scope du spec).

## GET /

Affiche le formulaire de soumission, avec deux entrées possibles pour une même évaluation.

- **Réponse**: 200, page HTML contenant :
  - un champ texte `repo_url` (mode dépôt) ;
  - un champ texte `documentation_texte` et/ou un champ d'upload `documentation_fichier` (mode
    documentation) ;
  - un bouton de soumission unique.

## POST /evaluate

Déclenche une évaluation complète (mode déterminé automatiquement à partir des champs soumis,
FR-001) et affiche le rapport (ou une erreur) sur la même page (FR-001a), avec une option de
téléchargement (FR-001b).

**Requête** (form-encoded/multipart, soumission du formulaire de `GET /`):

| Champ | Type | Règle |
|---|---|---|
| `repo_url` | string, optionnel | URL du dépôt GitHub public (FR-001). Si valide, détermine le mode dépôt. |
| `documentation_texte` | string, optionnel | Texte de documentation collé (FR-001, mode documentation) |
| `documentation_fichier` | fichier, optionnel | Fichier de documentation téléversé (FR-001, mode documentation) |

**Résolution du mode** (FR-001, research.md §8) : `repo_url` valide → mode dépôt (les champs
documentation, s'ils sont également remplis, sont ignorés et signalés dans `avertissements`) ;
sinon `documentation_texte` ou `documentation_fichier` non vide → mode documentation ; sinon,
requête rejetée (aucun mode déterminable).

**Réponses**:

| Cas | Statut | Contenu |
|---|---|---|
| Aucune entrée exploitable (ni URL valide, ni documentation) | 200 (page ré-affichée) ou 422 | Message d'erreur clair, aucun appel GitHub/LLM déclenché (FR-001, Edge Cases) |
| Dépôt privé ou inexistant (mode dépôt) | 200 (page ré-affichée) | Message d'erreur clair distinguant ce cas, aucun appel LLM déclenché (FR-002, SC-006) |
| Limitation de débit GitHub (mode dépôt) | 200 (page ré-affichée) | Message d'erreur clair distinguant cette cause d'un dépôt invalide (Edge Cases) |
| Documentation vide, illisible ou fichier non exploitable (mode documentation) | 200 (page ré-affichée) ou 422 | Message d'erreur clair, aucun appel LLM déclenché (Edge Cases) |
| Réponse LLM invalide/vide/inexploitable | 200, rapport HTML | Rapport produit quand même ; section AI Act (et liste de non-conformités) indique explicitement l'échec de cette analyse (Edge Cases, `ProfilAiAct.echec = true`) ; les détections RGPD restent présentes |
| Aucun fichier/contenu pertinent (AI Act et RGPD) | 200, rapport HTML | Rapport indique explicitement l'absence d'éléments détectés (Acceptance Scenario US1.3) |
| Aucune détection RGPD | 200, rapport HTML | Rapport mentionne explicitement l'absence de détection plutôt que d'omettre la section (Edge Cases) |
| Aucune non-conformité identifiée | 200, rapport HTML | Rapport mentionne explicitement l'absence de point identifié plutôt que d'omettre la section (US2 Acceptance Scenario 3) |
| Aucun passage légal pertinent récupéré pour un aspect détecté | 200, rapport HTML | Cet aspect n'est pas transformé en non-conformité ni en citation inventée ; le rapport signale l'absence de référence disponible (US2 Acceptance Scenario 4) |
| Succès complet | 200, rapport HTML | Page HTML structurée (FR-012) présentant `RapportFinal` (data-model.md) : profil AI Act, détections RGPD, liste de non-conformités, citations légales, nombre d'appels LLM effectués et taille envoyée par appel (FR-015), et un lien/bouton de téléchargement (FR-001b) |

**Invariants observables depuis ce contrat** (dérivés des Success Criteria) :

- Aucune réponse ne dépasse 3 minutes pour un dépôt de moins de 1000 fichiers (SC-001).
- Le nombre d'appels LLM effectués pendant le traitement d'une requête `POST /evaluate` est
  toujours ≤ 2 (FR-009, SC-002), et visible dans la page rendue (FR-015).
- Aucune citation légale affichée (profil AI Act ou non-conformités) ne peut référencer un passage
  qui n'a pas été effectivement récupéré par le composant RAG pour cette requête précise
  (FR-013/FR-019, SC-003) — la recherche RAG elle-même ne déclenche aucun appel LLM payant
  (FR-018).
- Aucune valeur brute de donnée personnelle détectée n'apparaît dans la réponse HTML — seulement
  des extraits masqués (FR-010a).
- La réponse ne déclenche aucune écriture de persistance côté serveur (FR-017), y compris pour la
  génération du téléchargement (FR-001b) : elle est entièrement dérivée de la requête courante.
- En mode documentation, aucun appel à l'API GitHub n'est effectué (FR-002a, SC-007).

## GET /evaluate/download (ou équivalent — lien généré dans la réponse de POST /evaluate)

Permet le téléchargement du rapport de la requête `POST /evaluate` qui vient d'être traitée
(FR-001b, US5). Aucune identification/récupération ultérieure d'un rapport passé n'est possible
(non-persistance, FR-017) : ce téléchargement fait partie du même cycle requête/réponse que
l'évaluation elle-même (ex. un second bouton de soumission renvoyant le même rendu en pièce
jointe, ou une réponse à double contenu — détail d'implémentation laissé à `tasks.md`).

- **Réponse**: 200, corps identique au rapport affiché (même `RapportFinal`), avec un en-tête
  `Content-Disposition: attachment` déclenchant le téléchargement navigateur ; aucune écriture
  serveur (FR-017).

## Non-buts (hors scope de ce contrat)

- Pas d'authentification utilisateur (dépôt ciblé toujours public, FR-002).
- Pas d'endpoint de récupération d'un rapport après la fin du cycle requête/réponse qui l'a produit
  (non-persistance, FR-017) : un rapport non téléchargé par l'utilisateur au moment de sa
  génération n'est pas récupérable après coup.
- Pas de format de téléchargement alternatif (PDF) en V1 — export du même rendu HTML structuré
  (clarification du 2026-09-16, Assumptions du spec).
- Pas d'API JSON publique séparée pour interroger le composant RAG ou le corpus juridique
  directement.
