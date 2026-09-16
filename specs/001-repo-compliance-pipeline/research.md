# Phase 0 Research: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Toutes les inconnues de la section Technical Context du plan ont été résolues ci-dessous ; aucun
`NEEDS CLARIFICATION` ne subsiste. Sections 7 et 8 ajoutées lors de l'amendement du 2026-09-16
(RAG, second mode d'entrée).

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
- **Reproductibilité (Principe III)** : l'appel LLM (`llm_client.py`) DOIT être fait avec une
  température de 0 (ou la valeur la plus basse disponible) et des instructions de sortie
  strictement structurées (JSON, échelle fermée pour `niveau_autonomie_decisionnelle`, FR-007a),
  afin de maximiser la reproductibilité d'une évaluation à l'autre pour un même contenu source et
  un même index RAG. Une reproductibilité stricte au caractère près n'est pas garantissable pour
  un texte libre généré par LLM (nature probabiliste du modèle) ; ce qui DOIT rester strictement
  reproductible est la partie déterministe du pipeline (sélection de fichiers, scan RGPD,
  récupération RAG) et la structure/les citations du profil AI Act, pas la formulation exacte du
  texte en langage clair.

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

## 7. Composant RAG pour la récupération des citations légales

- **Decision**: `sentence-transformers` avec un modèle d'embedding open-source léger multilingue
  (ex. famille `paraphrase-multilingual-MiniLM-L12-v2`, à confirmer/ajuster en tâche
  d'implémentation selon la couverture FR/EN du corpus), exécuté **localement**. Un script hors
  ligne (`services/legal_rag/build_index.py`) encode une fois chaque passage du corpus juridique
  (découpé par article/annexe ou par paragraphe si un article est long) et écrit les vecteurs
  résultants dans un fichier plat versionné (`src/data/legal_corpus/index.*`) avec, pour chaque
  vecteur, sa référence (`id_reference`) et son texte. À l'exécution, `retriever.py` encode
  uniquement la requête (profil/texte source condensé) avec le même modèle, puis calcule une
  similarité cosinus (`numpy`) contre les vecteurs pré-calculés pour retourner le top-N (N borné,
  ex. 5 à 10) des passages les plus pertinents.
- **Rationale**: FR-018 exige une indexation/recherche sans appel LLM ; FR-019 exige que seuls les
  passages effectivement récupérés soient citables. Un modèle d'embedding local répond aux deux
  sans coût API ni dépendance réseau à l'exécution — cohérent avec le budget (SC-004) puisque
  l'indexation ne se fait qu'une fois, hors ligne, et la recherche à l'exécution n'appelle jamais
  de service payant. Une recherche cosinus en mémoire via `numpy` suffit à la taille attendue d'un
  corpus AI Act + RGPD (quelques centaines de passages au plus), évitant d'introduire une base
  vectorielle externe (FAISS ou autre) à héberger — cohérent avec le Principe V (simplicité) et
  avec l'absence de persistance/infrastructure supplémentaire (FR-017 ne s'applique pas à l'index,
  qui est un artefact statique du corpus, pas une donnée de requête).
- **Alternatives considered**: Appel à une API d'embedding payante (ex. API Anthropic/OpenAI
  embeddings) — écarté : introduirait un coût récurrent par évaluation et une dépendance réseau
  supplémentaire non nécessaire pour un corpus fixe qui peut être encodé une seule fois hors ligne.
  Recherche purement lexicale (BM25/TF-IDF) — plus simple encore et écartée uniquement parce que le
  commanditaire a explicitement demandé un RAG à base d'embeddings ; reste une alternative de repli
  si la qualité de récupération sémantique s'avère insuffisante en pratique. Base vectorielle
  externe (ex. Qdrant, Pinecone) — écartée : sur-dimensionnée pour un corpus de taille modeste et
  contraire au Principe V (nouvelle infrastructure à héberger et maintenir).
- **Conséquence sur FR-007/FR-008**: le prompt de l'appel LLM unique inclut désormais le contenu
  source ET les passages récupérés ; les deux sont comptés dans le plafond de 40 000 caractères
  (FR-008), avec priorité de troncature au contenu source si nécessaire (les passages récupérés,
  plus courts et ciblés, sont conservés en priorité pour garantir des citations ancrées).

## 8. Second mode d'entrée : documentation fournie directement

- **Decision**: Le formulaire web accepte soit un champ URL (mode dépôt), soit un champ texte
  libre et/ou un champ d'upload de fichier (mode documentation) ; `services/input_router.py`
  détermine le mode selon une règle simple et déterministe : une URL GitHub valide dans le champ
  URL → mode dépôt (le contenu du champ documentation, s'il est rempli en parallèle, est ignoré et
  signalé, cf. Assumptions du spec) ; sinon, un contenu non vide dans le champ documentation ou un
  fichier téléversé → mode documentation ; ni l'un ni l'autre → rejet (FR-001, Edge Cases).
- **Rationale**: Réutilise directement la même conclusion de FR-001 (un seul point d'entrée
  formulaire, un seul mode actif par soumission) sans complexifier le contrat web avec des routes
  séparées. En mode documentation, `github_client.py` et `file_selector.py` ne sont simplement pas
  invoqués (FR-002a, FR-006a) ; le contenu fourni remplace directement `SelectionAiAct`/
  `SelectionRgpd` comme source, avec la même règle de troncature au plafond de 40 000 caractères.
- **Alternatives considered**: Deux formulaires/pages séparés selon le mode — écarté, ajoute une
  surface d'interface sans bénéfice fonctionnel (contraire au Principe V et à la demande explicite
  de ne pas complexifier l'UI). Détection automatique du mode par heuristique sur le contenu du
  champ texte (ex. deviner si c'est une URL) plutôt que deux champs distincts — écarté au profit de
  deux champs explicites, plus robuste et sans ambiguïté pour l'utilisateur et pour les tests.

## Résumé

Toutes les décisions techniques sont alignées avec les contraintes dures du spec (FR-001, FR-002,
FR-006, FR-008, FR-009, FR-010, FR-013, FR-017, FR-018, FR-019) et avec les cinq principes de la
constitution. Aucun point ne nécessite d'arbitrage supplémentaire avant la conception détaillée
(Phase 1).
