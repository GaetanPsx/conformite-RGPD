# Phase 0 Research: Pipeline d'extraction et d'analyse de conformité de dépôt GitHub

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Toutes les inconnues de la section Technical Context du plan ont été résolues ci-dessous ; aucun
`NEEDS CLARIFICATION` ne subsiste.

## 1. Framework web

- **Decision**: FastAPI, avec rendu server-side des pages via Jinja2 (pas d'API JSON séparée pour
  la V1).
- **Rationale**: Le besoin (FR-001, FR-001a) est un formulaire simple + affichage HTML du
  résultat dans le même navigateur, sans état partagé entre utilisateurs. FastAPI donne une
  validation de requête intégrée (utile pour FR-001, validation du format d'URL), un typage clair
  des entités (aligné avec `src/models/`), et reste un service unique — cohérent avec le Principe
  V (Simplicité). Un framework plus lourd (Django) apporterait un ORM et une couche admin
  inutiles puisqu'il n'y a aucune persistance (FR-017).
- **Alternatives considered**: Flask (plus minimal mais sans validation de schéma intégrée,
  demanderait une dépendance supplémentaire type Pydantic ajoutée manuellement — FastAPI l'inclut
  déjà) ; Django (trop de fonctionnalités non utilisées : ORM, admin, sessions persistantes,
  contraire à FR-017).

## 2. Accès à l'API GitHub

- **Decision**: API REST GitHub publique non authentifiée (`GET /repos/{owner}/{repo}` pour
  valider l'existence/visibilité, puis `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1`
  pour lister les chemins de fichiers sans télécharger leur contenu), via `httpx`.
- **Rationale**: FR-002 interdit explicitement tout flux OAuth ; l'API REST publique convient pour
  lister les arborescences sans authentification. L'endpoint "trees recursive" renvoie les chemins
  et tailles sans contenu, correspondant exactement à FR-003.
- **Alternatives considered**: GraphQL API GitHub (nécessite un token, donc une authentification —
  écarté par FR-002) ; clonage `git` complet du dépôt (télécharge le contenu de tous les fichiers,
  contraire à FR-003 et beaucoup plus lent, menaçant SC-001).
- **Rate limiting**: Le mode non authentifié est limité à 60 requêtes/heure par IP source ; le
  pipeline n'utilise que 1–2 requêtes GitHub par évaluation (métadonnées + arborescence), ce qui
  reste soutenable pour l'usage étudiant décrit dans Scale/Scope. Un 403/429 de GitHub est
  distingué d'un 404 (dépôt introuvable/privé) pour respecter l'edge case dédié du spec.

## 3. Fournisseur et modèle LLM

- **Decision**: Anthropic Claude API, modèle de la famille Haiku (le moins coûteux), pour l'unique
  appel d'inférence AI Act (FR-007).
- **Rationale**: Budget cumulé de 10€ sur 100 évaluations (SC-004) avec un plafond de 40 000
  caractères par appel (~10k tokens) impose un modèle à bas coût par token. Un seul appel par
  évaluation (FR-009) rend le choix du modèle peu sensible à la latence, donc la contrainte
  dominante est le coût par token plutôt que la vitesse.
- **Alternatives considered**: Un modèle plus capable (ex. famille Sonnet/Opus) donnerait
  potentiellement une meilleure qualité d'extraction mais au prix d'un coût par appel plusieurs
  fois supérieur, menaçant SC-004 sans bénéfice fonctionnel évident pour une tâche d'extraction
  structurée (secteur/finalité/autonomie) qui ne demande pas un raisonnement complexe.

## 4. Détection RGPD par motifs

- **Decision**: Bibliothèque standard `re` (Python), avec un jeu d'expressions régulières
  maintenu dans le code (une par catégorie : identité, contact, identifiant national, santé,
  biométrie, origine/croyances), aucune dépendance externe de type NLP/ML.
- **Rationale**: FR-010 exige explicitement une détection par motifs déterministes sans appel LLM.
  `re` est suffisant pour des motifs structurés (emails, IBAN-like, numéros de sécurité sociale,
  formats de date de naissance, mots-clés de santé/origine dans des noms de colonnes/fixtures) et
  ne introduit aucune dépendance supplémentaire (Principe V). Le taux de détection cible (SC-005,
  ≥90% sur un jeu de test représentatif) est atteignable avec des motifs bien choisis pour des
  formats connus.
- **Alternatives considered**: Un modèle NER (reconnaissance d'entités nommées) apporterait un
  meilleur rappel sur du texte libre non structuré, mais violerait FR-010 (interdiction d'appel
  LLM) et ajouterait une dépendance ML lourde pour un gain hors scope (le spec cible des fichiers
  de données structurés : schémas SQL, fixtures, configs — pas du texte libre).

## 5. Masquage des extraits détectés (FR-010a)

- **Decision**: Fonction de masquage déterministe par catégorie (ex. email → `j***@***.com` :
  premier caractère du local-part + domaine de premier niveau uniquement ; numéro national →
  seuls les 2 derniers chiffres visibles), appliquée immédiatement après la détection, avant toute
  autre étape (fusion du profil, rendu du rapport, journalisation).
- **Rationale**: FR-010a interdit de reproduire la valeur complète ; masquer au plus près du point
  de détection garantit qu'aucune valeur complète ne transite jamais vers les couches en aval
  (report_builder, logs), ce qui simplifie l'audit du Principe IV (aucun composant en aval n'a
  besoin d'accéder à la valeur brute).
- **Alternatives considered**: Masquer seulement au moment du rendu HTML final — rejeté car cela
  laisserait la valeur complète circuler en clair dans le profil combiné et les logs internes,
  augmentant la surface de risque sans bénéfice.

## 6. Tests contre des services externes (GitHub, LLM)

- **Decision**: `pytest` + `respx` (mock HTTP pour `httpx`) pour enregistrer des réponses
  représentatives de l'API GitHub et de l'API Anthropic, exécutées en CI sans réseau ni coût réel.
- **Rationale**: Le Principe II (Test-First, non négociable) exige des tests reproductibles pour
  chaque règle ; des appels réseau réels rendraient les tests non déterministes, lents, et
  consommeraient le budget LLM (SC-004) à chaque exécution de CI. `respx` s'intègre nativement
  avec `httpx`, déjà choisi comme client HTTP.
- **Alternatives considered**: `responses` (cible `requests`, pas `httpx` — incompatible avec le
  choix de client) ; appels réels dans un environnement de test dédié (rejeté : coût récurrent et
  non-déterminisme, contraire à l'Auditabilité du Principe III).

## Résumé

Toutes les décisions techniques sont alignées avec les contraintes dures du spec (FR-002, FR-006,
FR-008, FR-009, FR-010, FR-017) et avec les cinq principes de la constitution. Aucun point ne
nécessite d'arbitrage supplémentaire avant la conception détaillée (Phase 1).
