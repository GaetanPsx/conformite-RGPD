# Data Model: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Toutes les entités de requête ci-dessous vivent en mémoire pour la durée d'une requête HTTP ;
aucune n'est persistée (FR-017). Seul le `CorpusJuridique` (et son index vectoriel) est une
ressource statique versionnée, construite hors ligne une fois (research.md §7). Elles
correspondent à la section "Key Entities" du spec, précisées avec des champs et règles de
validation dérivés des Functional Requirements.

## DepotCible

Le dépôt GitHub public soumis pour évaluation (mode dépôt).

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

## DocumentationFournie

La documentation de projet soumise directement par l'utilisateur, en alternative à `DepotCible`
(mode documentation, FR-001/FR-002a).

| Champ | Type | Règle |
|---|---|---|
| `source` | enum | `"texte_colle"` ou `"fichier_televerse"` |
| `contenu` | string | Contenu brut fourni ; DOIT être non vide et exploitable comme texte (FR-016, Edge Cases : rejet si vide/illisible/binaire) |
| `nom_fichier` | string \| null | Nom du fichier si `source = "fichier_televerse"` ; `null` sinon |
| `tronque` | bool | `true` si `contenu` a dû être tronqué pour respecter le plafond de 40 000 caractères (FR-006a) |

**Mode exclusif**: une évaluation utilise soit `DepotCible`, soit `DocumentationFournie`, jamais
les deux (règle de résolution en cas de double soumission : voir Assumptions du spec et
`ModeEntree` ci-dessous).

## ModeEntree (résultat du routage d'entrée)

Résultat de la détermination automatique du mode, calculé une fois par évaluation (FR-001,
research.md §8).

| Champ | Type | Règle |
|---|---|---|
| `mode` | enum | `"depot"` ou `"documentation"` |
| `source_ignoree` | bool | `true` si l'utilisateur a fourni les deux entrées et que l'une a été ignorée (mode dépôt privilégié) ; le rapport le signale dans ce cas |

## FichierDepot

Un chemin de fichier listé dans le dépôt, avec métadonnées disponibles sans téléchargement de
contenu (FR-003, mode dépôt uniquement).

| Champ | Type | Règle |
|---|---|---|
| `chemin` | string | Chemin complet relatif à la racine du dépôt |
| `taille_octets` | int \| null | Fournie par l'API GitHub si disponible |
| `extension` | string \| null | Dérivée de `chemin` |
| `profondeur` | int | Nombre de séparateurs `/` dans `chemin` ; utilisée pour le tri de sélection (FR-006) |

## SelectionAiAct

Contenu source retenu pour l'analyse AI Act : sous-ensemble borné de `FichierDepot` en mode dépôt,
ou `DocumentationFournie` directement en mode documentation (FR-006/FR-006a).

| Champ | Type | Règle |
|---|---|---|
| `fichiers` | list[FichierAvecContenu] | Mode dépôt : ≤ 15 éléments (FR-006). Mode documentation : liste à un seul élément synthétique représentant `DocumentationFournie` |
| `selection_partielle` | bool | `true` si plus de 15 fichiers pertinents existaient en mode dépôt (Edge Cases) ; toujours `false` en mode documentation |
| `taille_totale_caracteres` | int | Somme des contenus après troncature ; DOIT être ≤ 40 000 moins la taille réservée aux passages RAG (FR-008) |

**Règle de sélection (FR-006, précisée en clarification, mode dépôt)** : (1) README et manifeste
de dépendances en premier ; (2) puis tri par `profondeur` croissante ; (3) puis, à profondeur
égale, tri alphabétique de `chemin`. Un fichier binaire, illisible en texte, ou dépassant à lui
seul le plafond est exclu ou tronqué avant inclusion (Edge Cases).

## SelectionRgpd

Contenu source retenu pour la détection RGPD : mêmes règles que `SelectionAiAct` (sous-ensemble de
`FichierDepot` en mode dépôt, ou `DocumentationFournie` en mode documentation), appliquées
indépendamment (limite séparée de 15 fichiers en mode dépôt).

| Champ | Type | Règle |
|---|---|---|
| `fichiers` | list[FichierAvecContenu] | Idem `SelectionAiAct` |
| `selection_partielle` | bool | Idem `SelectionAiAct` |

## FichierAvecContenu (type partagé)

| Champ | Type | Règle |
|---|---|---|
| `fichier` | FichierDepot \| DocumentationFournie | — |
| `contenu` | string | Tronqué si nécessaire pour respecter le plafond de la sélection parente |
| `tronque` | bool | `true` si le contenu a été coupé |

## CorpusJuridique (ressource statique en lecture seule)

Ensemble des articles et annexes légaux connus du système (AI Act, RGPD), découpé en passages
indexables. Fourni séparément (Assumptions) ; modélisé comme données statiques versionnées
(`src/data/legal_corpus/`), pas comme entité mutable du pipeline.

| Champ | Type | Règle |
|---|---|---|
| `id_reference` | string | Identifiant unique du passage (ex. `AIACT-ART-6`, `RGPD-ART-9`) |
| `texte` | string \| null | Texte du passage, fourni séparément (Assumptions) — hors scope de générer ce contenu ici |
| `theme` | string | Utilisé pour associer une référence à un élément détecté (ex. secteur, catégorie RGPD) |
| `embedding` | vector \| null | Vecteur pré-calculé par `build_index.py` (research.md §7), présent uniquement dans l'artefact d'index, pas dans le texte source du corpus |

**Invariant** : `CorpusJuridique` seul ne suffit pas à justifier une citation — seule une entrée
effectivement retournée comme `PassageLegalRecupere` pour l'évaluation en cours est citable
(FR-013/FR-019, renforcé par rapport à la version précédente qui autorisait toute entrée du
corpus).

## PassageLegalRecupere

Un passage du `CorpusJuridique` retourné par le composant de recherche légale (RAG) pour une
évaluation donnée (FR-018/FR-019).

| Champ | Type | Règle |
|---|---|---|
| `id_reference` | string | Référence vers `CorpusJuridique.id_reference` |
| `texte` | string | Copie du texte du passage au moment de la récupération (pour injection dans le prompt LLM) |
| `score_pertinence` | float | Score de similarité cosinus retourné par le retriever |

**Invariant (FR-019)** : seule la liste des `PassageLegalRecupere` produite pour une évaluation
donnée peut être citée dans `ProfilAiAct` ou `NonConformite` de cette même évaluation ; jamais un
`id_reference` du corpus qui n'aurait pas été récupéré par cette recherche.

## ProfilAiAct

Résultat structuré de l'unique appel LLM (FR-007), désormais enrichi par les passages RAG.

| Champ | Type | Règle |
|---|---|---|
| `secteur_activite` | string \| null | `null` si le LLM n'a pas pu être interprété (Edge Cases) |
| `finalite` | string \| null | Idem |
| `niveau_autonomie_decisionnelle` | string \| null | Idem — **ne détermine jamais un niveau de risque** (FR-014, cette valeur est une observation, pas un verdict) |
| `fichiers_source` | list[string] | Chemins des fichiers de `SelectionAiAct` (ou référence à `DocumentationFournie`) ayant servi de contexte |
| `passages_utilises` | list[PassageLegalRecupere.id_reference] | Passages effectivement cités pour ce profil |
| `echec` | bool | `true` si la réponse LLM était malformée/vide/inexploitable (Edge Cases) ; dans ce cas les champs ci-dessus sont `null` et le rapport DOIT signaler explicitement l'échec |

## DetectionRgpd

Une occurrence détectée d'une catégorie de donnée personnelle (FR-010).

| Champ | Type | Règle |
|---|---|---|
| `categorie` | enum | Une de : `identite`, `contact`, `identifiant_national`, `sante`, `biometrie`, `origine_croyances` |
| `source` | string | Chemin du fichier (mode dépôt) ou indication "documentation fournie" (mode documentation) |
| `motif` | string | Nom/identifiant de l'expression régulière ayant déclenché la détection (pour audit, Principe III) |
| `extrait_masque` | string | Extrait tronqué/masqué de la valeur trouvée (ex. `j***@***.com`) — **ne contient jamais la valeur complète** (FR-010a) |

**Invariant** : `extrait_masque` est calculé au point de détection (`rgpd_scanner.py`), avant
toute autre étape ; aucune structure du pipeline ne transporte la valeur brute au-delà de ce point
(cf. research.md §5).

## NonConformite

Un point de non-conformité potentiel identifié dans le rapport, en langage clair, rattaché à un
passage légal récupéré (FR-007, FR-012, FR-019 — nouvelle entité, réintégrée au scope).

| Champ | Type | Règle |
|---|---|---|
| `description` | string | Description en langage clair, destinée à un lecteur non technique |
| `passage_source` | PassageLegalRecupere.id_reference | DOIT référencer un passage effectivement récupéré pour cette évaluation (FR-013/FR-019) ; jamais `null` pour une entrée présente dans la liste |
| `origine` | enum | `"profil_aiact"` ou `"detection_rgpd"` — indique quelle partie du profil combiné a motivé ce point |

**Invariant** : si aucun passage suffisamment pertinent n'a été récupéré pour un aspect détecté du
profil, ce point n'est PAS transformé en `NonConformite` non justifiée ; le rapport signale
l'absence de référence disponible à la place (Edge Cases, US2 Acceptance Scenario 4).

## ProfilProjetCombine

Fusion structurée du profil AI Act, des détections RGPD, et de la liste de non-conformités
(FR-011).

| Champ | Type | Règle |
|---|---|---|
| `mode_entree` | ModeEntree | — |
| `depot` | DepotCible \| null | Renseigné uniquement en mode dépôt |
| `documentation` | DocumentationFournie \| null | Renseigné uniquement en mode documentation |
| `profil_aiact` | ProfilAiAct | — |
| `detections_rgpd` | list[DetectionRgpd] | Liste vide si aucune détection (le rapport le mentionne explicitement, Edge Cases) |
| `non_conformites` | list[NonConformite] | Liste vide si aucun point identifié (le rapport le mentionne explicitement, US2 Acceptance Scenario 3) |
| `appels_llm_effectues` | int | ≤ 2 (FR-009), exposé pour le suivi de budget (FR-015) |
| `taille_envoyee_par_appel` | list[int] | Une entrée par appel LLM (contenu source + passages RAG cumulés), exposée pour FR-015 |

## RapportFinal

Document HTML structuré, affiché dans le navigateur et téléchargeable, non persisté (FR-012,
FR-001b, FR-017).

| Champ | Type | Règle |
|---|---|---|
| `profil_combine` | ProfilProjetCombine | — |
| `citations` | list[PassageLegalRecupere.id_reference] | Résolues uniquement contre les passages récupérés pour cette évaluation (FR-013/FR-019) |
| `avertissements` | list[string] | Ex. "sélection partielle", "analyse AI Act échouée", "aucune donnée personnelle détectée", "aucune non-conformité identifiée", "entrée documentation ignorée au profit du dépôt" (Edge Cases) |
| `format` | const `"html"` | Rendu server-side via Jinja2 (clarification du 2026-09-16) |
| `telechargeable` | bool | Toujours `true` (FR-001b) ; le même rendu HTML est proposé en téléchargement, généré à la volée sans écriture serveur |

## Relations

```text
(DepotCible | DocumentationFournie) ──(ModeEntree)──> SelectionAiAct, SelectionRgpd

CorpusJuridique ──(build_index.py, hors ligne, 1 fois)──> index vectoriel versionné
index vectoriel ──(retriever.py, par évaluation)──> PassageLegalRecupere[*]

SelectionAiAct + PassageLegalRecupere[*] ──(1 appel LLM)──> ProfilAiAct + NonConformite[*]
SelectionRgpd ──(scan par motifs)──> DetectionRgpd[*]

ProfilAiAct + DetectionRgpd[*] + NonConformite[*] ──> ProfilProjetCombine
ProfilProjetCombine ─> RapportFinal (affiché + téléchargeable)
```
