# Quickstart: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/web-interface.md](./contracts/web-interface.md)

Ce guide valide de bout en bout que le pipeline fonctionne, sans dupliquer le détail des entités
(voir [data-model.md](./data-model.md)) ni du contrat web (voir
[contracts/web-interface.md](./contracts/web-interface.md)).

## Prérequis

- Python 3.11+
- Une clé API Anthropic valide dans la variable d'environnement `ANTHROPIC_API_KEY` (utilisée
  pour l'unique appel LLM payant, FR-007 ; voir research.md §3 pour le choix du modèle)
- Le modèle d'embedding local (`sentence-transformers`) téléchargé/mis en cache localement (aucune
  clé API requise pour ce composant, research.md §7)
- L'index vectoriel du corpus juridique déjà construit (`python -m src.services.legal_rag.build_index`,
  exécuté une fois — voir research.md §7 ; ne pas relancer à chaque évaluation)
- Accès réseau sortant vers `api.github.com` (non authentifié — aucun token requis, FR-002),
  uniquement nécessaire en mode dépôt
- Dépendances installées (`pip install -r requirements.txt`, une fois `src/` implémenté)

## Lancer le service localement

```bash
uvicorn src.web.app:app --reload
```

Ouvrir `http://localhost:8000/` dans un navigateur : le formulaire de soumission (`GET /`, cf.
contract) doit s'afficher, avec un champ URL de dépôt et un champ/upload de documentation.

## Scénario de validation 1 — Rapport complet en mode dépôt (US1, P1)

1. Soumettre l'URL d'un dépôt public réel contenant un README, un fichier de dépendances, du code
   d'inférence/modèle, et des fichiers de données (schémas SQL ou fixtures).
2. **Attendu** : la page affiche un rapport HTML structuré contenant :
   - un secteur d'activité, une finalité et un niveau d'autonomie décisionnelle, chacun avec au
     moins une citation légale correspondant à un passage récupéré par le RAG ;
   - une liste des catégories de données personnelles détectées, avec source et extrait masqué
     (jamais la valeur complète) ;
   - une liste de points de non-conformité potentiels, chacun rattaché à une référence légale ;
   - le nombre d'appels LLM effectués (doit être ≤ 2, typiquement 1) et la taille envoyée ;
   - un bouton/lien de téléchargement du rapport.
3. **Vérifie**: Acceptance Scenarios 1–2 de US1, US2, FR-007, FR-010a, FR-012, FR-015, FR-019.

## Scénario de validation 2 — Rapport complet en mode documentation (US1, P1)

1. Sur `GET /`, coller un texte de documentation de projet décrivant un système d'IA (secteur,
   finalité, éventuellement des exemples de schéma de données) dans le champ documentation, sans
   renseigner `repo_url`.
2. Soumettre.
3. **Attendu** : un rapport de structure équivalente au scénario 1 est produit, et aucun appel à
   l'API GitHub n'a été effectué pendant le traitement (vérifiable via les logs/mocks réseau).
4. **Vérifie**: Acceptance Scenarios 4–5 de US1, FR-001, FR-002a, FR-006a, SC-007.

## Scénario de validation 3 — Non-conformités ancrées dans le RAG (US2, P1)

1. Soumettre un dépôt ou une documentation présentant une caractéristique connue de non-conformité
   potentielle sur un point couvert par le corpus de test (ex. absence de mention de base légale
   pour un traitement de données de santé).
2. **Attendu** : le rapport contient une entrée de non-conformité correspondante, avec une
   référence légale précise.
3. **Vérifie**: que cette référence correspond à un passage listé dans les `PassageLegalRecupere`
   effectivement retournés pour cette évaluation (et non une référence arbitraire du corpus) —
   Acceptance Scenarios de US2, FR-013, FR-019, SC-003, SC-008.
4. Soumettre un second cas ne présentant aucune caractéristique de non-conformité couverte par le
   corpus de test et vérifier que le rapport indique explicitement l'absence de point identifié
   (US2 Acceptance Scenario 3).

## Scénario de validation 4 — Budget LLM strict (US3, P2)

1. Soumettre l'URL d'un dépôt volumineux (plusieurs centaines de fichiers).
2. **Attendu** : la sélection AI Act et la sélection RGPD sont chacune bornées à 15 fichiers
   maximum ; le rapport ou les logs indiquent que la sélection est partielle
   (`selection_partielle = true`).
3. **Vérifie**: qu'au maximum 2 appels LLM payants ont été effectués au total (compter dans les
   logs ou le champ exposé par FR-015), qu'aucun appel n'a envoyé plus de 40 000 caractères
   (contenu source + passages RAG cumulés), et que la recherche RAG elle-même n'apparaît pas dans
   ce compteur (recherche locale, FR-018).
4. **Vérifie**: Acceptance Scenarios de US3, FR-006, FR-008, FR-009, SC-002.

## Scénario de validation 5 — Détection RGPD sans LLM (US4, P3)

1. Préparer un petit dépôt de test (ou une documentation de test) avec des fichiers de données
   contenant des motifs connus (un email, un numéro de sécurité sociale, un identifiant de santé)
   et un contenu sans aucun motif.
2. Soumettre.
3. **Attendu** : les catégories correspondantes sont détectées avec un extrait masqué et la
   source ; le contenu sans motif ne génère aucune détection.
4. **Vérifie**: qu'aucun appel LLM n'est comptabilisé pour cette étape (le compteur d'appels LLM
   de FR-015 doit rester inchangé entre une entrée avec et sans fichiers AI Act pertinents, toutes
   choses égales par ailleurs) — Acceptance Scenarios de US4, FR-010, FR-010a.

## Scénario de validation 6 — Téléchargement du rapport (US5, P3)

1. Après un rapport généré (scénario 1 ou 2), déclencher le téléchargement depuis l'interface.
2. **Attendu** : le fichier téléchargé contient l'intégralité du rapport affiché (profil,
   détections RGPD, non-conformités, citations).
3. **Vérifie**: qu'aucune écriture serveur (fichier, base de données) n'a eu lieu pour produire ce
   téléchargement — Acceptance Scenarios de US5, FR-001b, FR-017, SC-009.

## Scénarios d'erreur (Edge Cases)

| Entrée | Attendu |
|---|---|
| URL d'un dépôt privé ou inexistant, sans documentation alternative | Message d'erreur clair, 0 appel LLM (SC-006) |
| URL qui n'est pas une URL GitHub valide, sans documentation alternative | Rejet immédiat par validation de format (FR-001) |
| Ni URL valide ni documentation fournie | Rejet avec message clair indiquant qu'une des deux entrées est requise (FR-001, Acceptance Scenario US1.6) |
| URL valide ET documentation fournie simultanément | Mode dépôt privilégié, documentation ignorée et signalée dans les avertissements du rapport (Assumptions) |
| Documentation vide, illisible ou fichier binaire | Rejet avec message clair, 0 appel LLM (Edge Cases) |
| Dépôt/documentation sans aucun contenu pertinent AI Act ni RGPD | Rapport indique explicitement l'absence d'éléments détectés (Acceptance Scenario 3, US1) |
| Réponse LLM malformée (simuler via un mock en test) | Rapport produit quand même, section AI Act et liste de non-conformités marquées en échec explicite |
| Aucun passage RAG pertinent pour un aspect détecté | Aspect non transformé en non-conformité inventée ; absence de référence signalée (US2 Acceptance Scenario 4) |

## Vérification du budget global (SC-004)

Exécuter la suite de scénarios ci-dessus plusieurs fois et suivre la somme du champ
`taille_envoyee_par_appel` (FR-015) à travers un nombre représentatif d'évaluations pour projeter
le coût cumulé sur 100 évaluations et confirmer qu'il reste sous 10€ (voir research.md §3 pour le
choix du modèle LLM et son tarif). L'indexation RAG (research.md §7), exécutée une seule fois hors
ligne, n'entre pas dans ce budget récurrent.

## Tests automatisés

Les scénarios ci-dessus doivent être couverts par `tests/integration/` avec les appels GitHub et
LLM simulés (voir research.md §6 — `respx`) pour les deux modes d'entrée, et chaque règle de
sélection/détection/récupération RAG doit avoir un cas conforme et un cas non conforme dans
`tests/unit/` (Principe II de la constitution), y compris la récupération RAG testée contre un
index pré-calculé figé (pas de réentraînement en CI). Le détail des cas de test et leur
séquencement est produit par `/speckit-tasks`, pas par ce guide.
