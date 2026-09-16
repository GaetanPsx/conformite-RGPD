# Contract: Interface web

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

Le système expose une seule surface d'interaction : une interface web server-rendered (FastAPI +
Jinja2, cf. research.md §1). Pas d'API JSON publique en V1 (hors scope du spec).

## GET /

Affiche le formulaire de soumission d'URL.

- **Réponse**: 200, page HTML contenant un champ texte `repo_url` et un bouton de soumission.

## POST /evaluate

Déclenche une évaluation complète et affiche le rapport (ou une erreur) sur la même page
(FR-001a).

**Requête** (form-encoded, soumission du formulaire de `GET /`):

| Champ | Type | Règle |
|---|---|---|
| `repo_url` | string | URL du dépôt GitHub public (FR-001) |

**Réponses**:

| Cas | Statut | Contenu |
|---|---|---|
| URL malformée (ne matche pas le format GitHub attendu) | 200 (page ré-affichée) ou 422 | Message d'erreur clair, aucun appel GitHub/LLM déclenché (FR-001, Edge Cases) |
| Dépôt privé ou inexistant | 200 (page ré-affichée) | Message d'erreur clair distinguant ce cas, aucun appel LLM déclenché (FR-002, SC-006) |
| Limitation de débit GitHub (rate limit) | 200 (page ré-affichée) | Message d'erreur clair distinguant cette cause d'un dépôt invalide (Edge Cases) |
| Réponse LLM invalide/vide/inexploitable | 200, rapport HTML | Rapport produit quand même ; section AI Act indique explicitement l'échec de cette analyse (Edge Cases, `ProfilAiAct.echec = true`) ; les détections RGPD restent présentes |
| Aucun fichier pertinent (AI Act et RGPD) | 200, rapport HTML | Rapport indique explicitement l'absence d'éléments détectés (Acceptance Scenario US1.3) |
| Aucune détection RGPD | 200, rapport HTML | Rapport mentionne explicitement l'absence de détection plutôt que d'omettre la section (Edge Cases) |
| Succès complet | 200, rapport HTML | Page HTML structurée (FR-012) présentant `RapportFinal` (data-model.md), incluant le nombre d'appels LLM effectués et la taille envoyée par appel (FR-015) |

**Invariants observables depuis ce contrat** (dérivés des Success Criteria) :

- Aucune réponse ne dépasse 3 minutes pour un dépôt de moins de 1000 fichiers (SC-001).
- Le nombre d'appels LLM effectués pendant le traitement d'une requête `POST /evaluate` est
  toujours ≤ 2 (FR-009, SC-002), et visible dans la page rendue (FR-015).
- Aucune citation légale affichée ne peut référencer un identifiant hors du corpus juridique
  statique (FR-013, SC-003).
- Aucune valeur brute de donnée personnelle détectée n'apparaît dans la réponse HTML — seulement
  des extraits masqués (FR-010a).
- La réponse ne déclenche aucune écriture de persistance côté serveur (FR-017) : elle est
  entièrement dérivée de la requête courante.

## Non-buts (hors scope de ce contrat)

- Pas d'authentification utilisateur (dépôt ciblé toujours public, FR-002).
- Pas d'endpoint de récupération ultérieure d'un rapport (non-persistance, FR-017) : un rapport
  non sauvegardé par l'utilisateur (ex. impression navigateur) n'est pas récupérable après coup.
- Pas de format de sortie alternatif (JSON, PDF) en V1 — seulement HTML structuré (clarification
  du 2026-09-16).
