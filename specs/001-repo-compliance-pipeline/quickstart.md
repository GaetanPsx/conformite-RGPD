# Quickstart: Pipeline d'extraction et d'analyse de conformité de dépôt GitHub

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/web-interface.md](./contracts/web-interface.md)

Ce guide valide de bout en bout que le pipeline fonctionne, sans dupliquer le détail des entités
(voir [data-model.md](./data-model.md)) ni du contrat web (voir
[contracts/web-interface.md](./contracts/web-interface.md)).

## Prérequis

- Python 3.11+
- Une clé API Anthropic valide dans la variable d'environnement `ANTHROPIC_API_KEY` (utilisée
  pour l'unique appel LLM, FR-007 ; voir research.md §3 pour le choix du modèle)
- Accès réseau sortant vers `api.github.com` (non authentifié — aucun token requis, FR-002)
- Dépendances installées (`pip install -r requirements.txt`, une fois `src/` implémenté)

## Lancer le service localement

```bash
uvicorn src.web.app:app --reload
```

Ouvrir `http://localhost:8000/` dans un navigateur : le formulaire de soumission d'URL
(`GET /`, cf. contract) doit s'afficher.

## Scénario de validation 1 — Rapport complet (US1, P1)

1. Soumettre l'URL d'un dépôt public réel contenant un README, un fichier de dépendances, du code
   d'inférence/modèle, et des fichiers de données (schémas SQL ou fixtures).
2. **Attendu** : la page affiche un rapport HTML structuré contenant :
   - un secteur d'activité, une finalité et un niveau d'autonomie décisionnelle, chacun avec au
     moins une citation légale ;
   - une liste des catégories de données personnelles détectées, avec fichier source et extrait
     masqué (jamais la valeur complète) ;
   - le nombre d'appels LLM effectués (doit être ≤ 2, typiquement 1) et la taille envoyée.
3. **Vérifie**: Acceptance Scenarios 1–2 de US1, FR-007, FR-010a, FR-015.

## Scénario de validation 2 — Budget LLM strict (US2, P2)

1. Soumettre l'URL d'un dépôt volumineux (plusieurs centaines de fichiers).
2. **Attendu** : la sélection AI Act et la sélection RGPD sont chacune bornées à 15 fichiers
   maximum ; le rapport ou les logs indiquent que la sélection est partielle
   (`selection_partielle = true`).
3. **Vérifie**: qu'au maximum 2 appels LLM ont été effectués au total (compter dans les logs ou le
   champ exposé par FR-015), et qu'aucun appel n'a envoyé plus de 40 000 caractères.
4. **Vérifie**: Acceptance Scenarios de US2, FR-006, FR-008, FR-009, SC-002.

## Scénario de validation 3 — Détection RGPD sans LLM (US3, P3)

1. Préparer un petit dépôt de test avec des fichiers de données contenant des motifs connus (un
   email, un numéro de sécurité sociale, un identifiant de santé) et un fichier sans aucun motif.
2. Soumettre son URL.
3. **Attendu** : les catégories correspondantes sont détectées avec un extrait masqué et le
   fichier source ; le fichier sans motif ne génère aucune détection.
4. **Vérifie**: qu'aucun appel LLM n'est comptabilisé pour cette étape (le compteur d'appels LLM
   de FR-015 doit rester inchangé entre un dépôt avec et sans fichiers AI Act pertinents, toutes
   choses égales par ailleurs) — Acceptance Scenarios de US3, FR-010, FR-010a.

## Scénarios d'erreur (Edge Cases)

| Entrée | Attendu |
|---|---|
| URL d'un dépôt privé ou inexistant | Message d'erreur clair, 0 appel LLM (SC-006) |
| URL qui n'est pas une URL GitHub valide | Rejet immédiat par validation de format (FR-001) |
| Dépôt sans aucun fichier pertinent AI Act ni RGPD | Rapport indique explicitement l'absence d'éléments détectés (Acceptance Scenario 3, US1) |
| Réponse LLM malformée (simuler via un mock en test) | Rapport produit quand même, section AI Act marquée en échec explicite |

## Vérification du budget global (SC-004)

Exécuter la suite de scénarios ci-dessus plusieurs fois et suivre la somme du champ
`taille_envoyee_par_appel` (FR-015) à travers un nombre représentatif d'évaluations pour projeter
le coût cumulé sur 100 évaluations et confirmer qu'il reste sous 10€ (voir research.md §3 pour le
choix du modèle LLM et son tarif).

## Tests automatisés

Les scénarios ci-dessus doivent être couverts par `tests/integration/` avec les appels GitHub et
LLM simulés (voir research.md §6 — `respx`), et chaque règle de sélection/détection doit avoir un
cas conforme et un cas non conforme dans `tests/unit/` (Principe II de la constitution). Le détail
des cas de test et leur séquencement est produit par `/speckit-tasks`, pas par ce guide.
