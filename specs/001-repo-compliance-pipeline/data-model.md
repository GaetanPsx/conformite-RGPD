# Data Model: Pipeline d'extraction et d'analyse de conformité de dépôt GitHub

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Toutes les entités ci-dessous vivent en mémoire pour la durée d'une requête HTTP ; aucune n'est
persistée (FR-017). Elles correspondent à la section "Key Entities" du spec, précisées avec des
champs et règles de validation dérivés des Functional Requirements.

## DepotCible

Le dépôt GitHub public soumis pour évaluation.

| Champ | Type | Règle |
|---|---|---|
| `url` | string | Fournie par l'utilisateur ; DOIT matcher le format `https://github.com/{owner}/{repo}` (FR-001) |
| `owner` | string | Extrait de `url` |
| `repo` | string | Extrait de `url` |
| `est_public` | bool | Résultat de la vérification GitHub (FR-002) ; si `false`, le pipeline s'arrête avec une erreur claire |
| `default_branch` | string | Nécessaire pour lister l'arborescence via l'API GitHub |

**Validation**: rejet immédiat (sans appel LLM, sans appel API au-delà de la vérification
d'accessibilité) si l'URL ne matche pas le format attendu, ou si `est_public` est `false` ou
indéterminable (dépôt inexistant) — cf. Edge Cases du spec.

## FichierDepot

Un chemin de fichier listé dans le dépôt, avec métadonnées disponibles sans téléchargement de
contenu (FR-003).

| Champ | Type | Règle |
|---|---|---|
| `chemin` | string | Chemin complet relatif à la racine du dépôt |
| `taille_octets` | int \| null | Fournie par l'API GitHub si disponible |
| `extension` | string \| null | Dérivée de `chemin` |
| `profondeur` | int | Nombre de séparateurs `/` dans `chemin` ; utilisée pour le tri de sélection (FR-006) |

## SelectionAiAct

Sous-ensemble borné de `FichierDepot` retenu pour l'analyse AI Act, avec leur contenu.

| Champ | Type | Règle |
|---|---|---|
| `fichiers` | list[FichierAvecContenu] | ≤ 15 éléments (FR-006) |
| `selection_partielle` | bool | `true` si plus de 15 fichiers pertinents existaient (Edge Cases) |
| `taille_totale_caracteres` | int | Somme des contenus après troncature ; DOIT être ≤ 40 000 (FR-008) |

**Règle de sélection (FR-006, précisée en clarification)** : (1) README et manifeste de
dépendances en premier ; (2) puis tri par `profondeur` croissante ; (3) puis, à profondeur égale,
tri alphabétique de `chemin`. Un fichier binaire, illisible en texte, ou dépassant à lui seul le
plafond est exclu ou tronqué avant inclusion (Edge Cases).

## SelectionRgpd

Sous-ensemble borné de `FichierDepot` retenu pour la détection RGPD, avec leur contenu. Mêmes
règles de sélection et de troncature que `SelectionAiAct`, appliquées indépendamment (limite
séparée de 15 fichiers).

| Champ | Type | Règle |
|---|---|---|
| `fichiers` | list[FichierAvecContenu] | ≤ 15 éléments (FR-006) |
| `selection_partielle` | bool | Idem `SelectionAiAct` |

## FichierAvecContenu (type partagé)

| Champ | Type | Règle |
|---|---|---|
| `fichier` | FichierDepot | — |
| `contenu` | string | Tronqué si nécessaire pour respecter le plafond de la sélection parente |
| `tronque` | bool | `true` si le contenu a été coupé |

## ProfilAiAct

Résultat structuré de l'unique appel LLM (FR-007).

| Champ | Type | Règle |
|---|---|---|
| `secteur_activite` | string \| null | `null` si le LLM n'a pas pu être interprété (Edge Cases) |
| `finalite` | string \| null | Idem |
| `niveau_autonomie_decisionnelle` | string \| null | Idem — **ne détermine jamais un niveau de risque** (FR-014, cette valeur est une observation, pas un verdict) |
| `fichiers_source` | list[string] | Chemins des fichiers de `SelectionAiAct` ayant servi de contexte |
| `echec` | bool | `true` si la réponse LLM était malformée/vide/inexploitable (Edge Cases) ; dans ce cas les champs ci-dessus sont `null` et le rapport DOIT signaler explicitement l'échec |

## DetectionRgpd

Une occurrence détectée d'une catégorie de donnée personnelle (FR-010).

| Champ | Type | Règle |
|---|---|---|
| `categorie` | enum | Une de : `identite`, `contact`, `identifiant_national`, `sante`, `biometrie`, `origine_croyances` |
| `fichier_source` | string | Chemin du fichier dans `SelectionRgpd` |
| `motif` | string | Nom/identifiant de l'expression régulière ayant déclenché la détection (pour audit, Principe III) |
| `extrait_masque` | string | Extrait tronqué/masqué de la valeur trouvée (ex. `j***@***.com`) — **ne contient jamais la valeur complète** (FR-010a) |

**Invariant** : `extrait_masque` est calculé au point de détection (`rgpd_scanner.py`), avant
toute autre étape ; aucune structure du pipeline ne transporte la valeur brute au-delà de ce point
(cf. research.md §5).

## ProfilProjetCombine

Fusion structurée du profil AI Act et des détections RGPD (FR-011).

| Champ | Type | Règle |
|---|---|---|
| `depot` | DepotCible | — |
| `profil_aiact` | ProfilAiAct | — |
| `detections_rgpd` | list[DetectionRgpd] | Liste vide si aucune détection (le rapport le mentionne explicitement, Edge Cases) |
| `appels_llm_effectues` | int | ≤ 2 (FR-009), exposé pour le suivi de budget (FR-015) |
| `taille_envoyee_par_appel` | list[int] | Une entrée par appel LLM, exposée pour FR-015 |

## CorpusJuridique (ressource statique en lecture seule)

Ensemble des articles et annexes légaux connus du système (AI Act, RGPD), source unique légitime
de citation (FR-013). Fourni séparément (Assumptions) ; modélisé ici comme données statiques
versionnées (`src/data/legal_corpus/`), pas comme entité mutable du pipeline.

| Champ | Type | Règle |
|---|---|---|
| `id_reference` | string | Identifiant unique (ex. `AIACT-ART-6`, `RGPD-ART-9`) |
| `texte` | string \| null | Corpus fourni séparément (Assumptions) — hors scope de générer ce contenu ici |
| `theme` | string | Utilisé pour associer une référence à un élément détecté (ex. secteur, catégorie RGPD) |

**Invariant (FR-013)** : toute citation apparaissant dans `RapportFinal` DOIT référencer un
`id_reference` existant dans ce corpus. En l'absence de correspondance, le rapport signale
explicitement l'absence de référence disponible plutôt que d'inventer une citation.

## RapportFinal

Document HTML structuré, affiché dans le navigateur, non persisté (FR-012, FR-017).

| Champ | Type | Règle |
|---|---|---|
| `profil_combine` | ProfilProjetCombine | — |
| `citations` | list[CorpusJuridique.id_reference] | Résolues contre `CorpusJuridique` uniquement (FR-013) |
| `avertissements` | list[string] | Ex. "sélection partielle", "analyse AI Act échouée", "aucune donnée personnelle détectée" (Edge Cases) |
| `format` | const `"html"` | Rendu server-side via Jinja2 (clarification du 2026-09-16) |

## Relations

```text
DepotCible 1──* FichierDepot
FichierDepot ──(sélection AI Act)──> SelectionAiAct.fichiers[*].fichier
FichierDepot ──(sélection RGPD)────> SelectionRgpd.fichiers[*].fichier
SelectionAiAct ──(1 appel LLM)─────> ProfilAiAct
SelectionRgpd ──(scan par motifs)──> DetectionRgpd[*]
ProfilAiAct + DetectionRgpd[*] ────> ProfilProjetCombine
ProfilProjetCombine + CorpusJuridique ─> RapportFinal
```
