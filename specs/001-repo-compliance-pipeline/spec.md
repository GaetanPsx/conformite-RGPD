# Feature Specification: Pipeline d'extraction et d'analyse de conformité de dépôt GitHub

**Feature Branch**: `001-repo-compliance-pipeline`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Construire le pipeline d'extraction et d'analyse d'un dépôt GitHub public pour évaluer sa conformité AI Act et RGPD."

## Clarifications

### Session 2026-09-16

- Q: Quand une catégorie de donnée personnelle est détectée dans un fichier, le rapport doit-il inclure l'extrait de texte réellement trouvé, ou seulement signaler la catégorie et sa localisation sans reproduire la donnée elle-même ? → A: Catégorie + extrait tronqué/masqué (ex. "j***@***.com") à titre de preuve, sans exposer la donnée complète.
- Q: Comment l'utilisateur soumet-il l'URL du dépôt et reçoit-il le rapport final ? → A: Via une interface web (formulaire de saisie de l'URL, affichage du rapport dans le navigateur).
- Q: Au-delà de "README et manifeste de dépendances en premier", quelle règle complète détermine l'ordre de priorité pour choisir les fichiers restants au-delà de la limite de 15 par catégorie ? → A: Profondeur de chemin croissante (racine d'abord) puis ordre alphabétique du chemin complet.
- Q: Le rapport généré (et les extraits de données détectés) doit-il être conservé par le système après affichage à l'utilisateur, ou est-il éphémère ? → A: Éphémère, non persisté — le rapport n'est conservé que le temps de la requête/session et n'est pas écrit en base de données ou sur disque au-delà de la réponse renvoyée au navigateur.
- Q: Dans quel format le rapport doit-il être affiché sur l'interface web ? → A: HTML structuré (sections, titres, listes), adapté à un lecteur non technique.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtenir un rapport de conformité à partir d'une URL de dépôt (Priority: P1)

En tant qu'utilisateur (développeur, product owner, DPO), je soumets, via une interface web,
l'URL d'un dépôt GitHub public et j'obtiens en retour, affiché dans mon navigateur, un rapport de
conformité en langage clair, couvrant à la fois l'AI Act et le RGPD, citant les articles/annexes
légaux pertinents, sans avoir à lire moi-même tout le code du dépôt.

**Why this priority**: C'est la valeur centrale du produit — sans cette capacité de bout en bout,
il n'y a pas de produit utilisable.

**Independent Test**: Soumettre l'URL d'un dépôt public réel contenant à la fois du code
d'inférence/modèle et des fichiers de données, et vérifier qu'un rapport structuré est produit,
contenant un profil AI Act, une liste de catégories de données personnelles détectées, et des
citations légales.

**Acceptance Scenarios**:

1. **Given** une URL de dépôt GitHub public valide contenant un README, un fichier de
   dépendances et du code de modèle/inférence, **When** l'utilisateur lance une évaluation,
   **Then** le système produit un rapport incluant un secteur d'activité, une finalité et un
   niveau d'autonomie décisionnelle déduits, chacun accompagné d'au moins une référence légale
   issue du corpus fourni.
2. **Given** une URL de dépôt GitHub public valide contenant des schémas SQL, des migrations ou
   des fixtures, **When** l'utilisateur lance une évaluation, **Then** le rapport liste les
   catégories de données personnelles détectées (identité, contact, identifiant national, santé,
   biométrie, origine/croyances) avec le fichier source de chaque détection.
3. **Given** un dépôt ne contenant aucun fichier pertinent pour l'AI Act ni pour le RGPD,
   **When** l'utilisateur lance une évaluation, **Then** le rapport indique explicitement
   l'absence d'éléments pertinents détectés plutôt que d'inventer un résultat.

---

### User Story 2 - Respecter un budget d'appels LLM strict (Priority: P2)

En tant qu'utilisateur responsable du budget du projet, je veux que chaque évaluation respecte
une limite stricte d'appels LLM et de taille de contenu envoyée, afin que le coût par évaluation
reste prévisible et compatible avec un budget total de 10€ pour l'ensemble du projet.

**Why this priority**: Le budget LLM est une contrainte dure explicitement posée par le
commanditaire ; la dépasser rend le produit inutilisable en pratique, même si le reste
fonctionne.

**Independent Test**: Exécuter une évaluation sur un dépôt volumineux (des centaines de
fichiers) et vérifier, via les journaux/compteurs exposés par le système, qu'au maximum 2 appels
LLM sont effectués au total et qu'aucun appel n'envoie un contenu dépassant le plafond de taille
configuré.

**Acceptance Scenarios**:

1. **Given** un dépôt contenant plus de fichiers pertinents que la limite configurée,
   **When** le système sélectionne les fichiers pour l'analyse AI Act, **Then** il ne retient
   qu'un sous-ensemble borné par la limite, choisi selon une règle de priorité déterministe.
2. **Given** une évaluation complète d'un dépôt, **When** l'évaluation se termine,
   **Then** le nombre total d'appels LLM effectués est au maximum 2, et ce nombre est visible
   dans le résultat ou les journaux de l'évaluation.
3. **Given** un fichier sélectionné dont le contenu dépasse le plafond de taille par appel,
   **When** ce fichier est inclus dans le contenu envoyé au LLM, **Then** son contenu est tronqué
   ou exclu avant l'envoi, de façon à respecter le plafond.

---

### User Story 3 - Détecter les données personnelles sans appel LLM (Priority: P3)

En tant qu'utilisateur, je veux que la détection des catégories de données personnelles dans les
fichiers de données soit effectuée uniquement par détection de motifs (sans appel à un LLM), afin
de garantir un coût nul, une exécution rapide et un résultat reproductible pour cette partie de
l'analyse.

**Why this priority**: C'est une contrainte de conception explicite qui conditionne le budget et
la fiabilité de la partie RGPD ; elle est indépendante de la partie AI Act et peut être livrée et
testée seule.

**Independent Test**: Fournir un dépôt de test contenant des fichiers de données avec des motifs
connus (adresses e-mail, numéros de sécurité sociale, identifiants de santé, etc.) et vérifier
que les catégories correspondantes sont détectées correctement, sans qu'aucun appel LLM ne soit
déclenché pendant cette étape.

**Acceptance Scenarios**:

1. **Given** un fichier de données contenant un motif reconnu d'identifiant national,
   **When** le scan RGPD s'exécute, **Then** la catégorie "identifiant national" est reportée
   avec le fichier source, sans qu'aucun appel LLM ne soit effectué pour cette détection.
2. **Given** un fichier de données ne contenant aucun motif de données personnelles connu,
   **When** le scan RGPD s'exécute, **Then** aucune catégorie n'est reportée pour ce fichier et
   le système ne signale pas de faux positif.

---

### Edge Cases

- Que se passe-t-il si l'URL fournie pointe vers un dépôt privé, inexistant, ou n'est pas une URL
  GitHub valide ? Le système doit rejeter la demande avec un message clair, sans déclencher
  d'appel LLM ni d'appel à l'API GitHub au-delà de la vérification d'accessibilité.
- Que se passe-t-il si le dépôt dépasse la limite de fichiers pertinents pour une ou les deux
  catégories (AI Act / RGPD) ? Le système sélectionne un sous-ensemble borné selon une règle de
  priorité déterministe et documente que la sélection est partielle.
- Que se passe-t-il si un fichier sélectionné est binaire, illisible en texte, ou dépasse la
  taille plafond à lui seul ? Il est exclu ou tronqué avant tout envoi au LLM ou scan de motifs.
- Que se passe-t-il si la réponse du LLM est malformée, vide, ou ne peut pas être interprétée ?
  Le système ne plante pas silencieusement ; le rapport final indique explicitement que l'analyse
  AI Act a échoué pour cette évaluation.
- Que se passe-t-il en cas de limitation de débit (rate limiting) de l'API GitHub non
  authentifiée ? Le système renvoie un message d'erreur clair distinguant cette cause d'un dépôt
  invalide.
- Que se passe-t-il si aucune catégorie de données personnelles n'est détectée dans tout le
  dépôt ? Le rapport le mentionne explicitement plutôt que d'omettre silencieusement la section.
- Que se passe-t-il si un article ou une annexe légale pertinent n'existe pas dans le corpus
  fourni ? Le rapport ne doit jamais inventer de référence ; il peut signaler l'absence de
  référence disponible pour ce point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT permettre à un utilisateur de fournir une URL de dépôt GitHub en
  entrée via une interface web (formulaire de saisie), et DOIT valider que cette URL correspond
  au format attendu avant de poursuivre.
- **FR-001a**: Le système DOIT afficher le rapport final dans le navigateur de l'utilisateur, sur
  la même interface web ayant servi à la soumission de l'URL.
- **FR-002**: Le système DOIT vérifier que le dépôt visé est public et accessible sans
  authentification, et DOIT rejeter clairement toute demande portant sur un dépôt privé ou
  inaccessible, sans mettre en œuvre de flux d'authentification OAuth.
- **FR-003**: Le système DOIT récupérer la liste des chemins de fichiers du dépôt sans
  télécharger le contenu de ces fichiers à cette étape.
- **FR-004**: Le système DOIT identifier, parmi la liste des fichiers, ceux pertinents pour
  l'AI Act (au minimum : README, fichiers de dépendances, code d'inférence/modèle).
- **FR-005**: Le système DOIT identifier, parmi la liste des fichiers, ceux pertinents pour le
  RGPD (au minimum : schémas SQL, fichiers de migration, fixtures, fichiers de configuration
  JSON).
- **FR-006**: Le système DOIT limiter le nombre de fichiers sélectionnés pour analyse à un
  maximum de 15 fichiers pour l'AI Act et 15 fichiers pour le RGPD par évaluation, en
  choisissant les fichiers selon la règle de priorité déterministe suivante lorsque plus de
  fichiers pertinents existent : (1) README et manifeste de dépendances en premier, (2) puis les
  fichiers restants triés par profondeur de chemin croissante (racine d'abord), (3) puis, à
  profondeur égale, par ordre alphabétique du chemin complet.
- **FR-007**: Le système DOIT envoyer le contenu des fichiers sélectionnés pour l'AI Act à un LLM,
  en un seul appel au maximum par évaluation, afin d'en déduire le secteur d'activité, la
  finalité, et le niveau d'autonomie décisionnelle du système analysé.
- **FR-008**: Le système DOIT plafonner la taille du contenu envoyé à chaque appel LLM à un
  maximum de 40 000 caractères au total (fichiers concaténés, tronqués si nécessaire pour
  respecter cette limite).
- **FR-009**: Le système DOIT garantir qu'une évaluation complète d'un dépôt n'effectue jamais
  plus de 2 appels LLM au total, tous usages confondus.
- **FR-010**: Le système DOIT scanner le contenu des fichiers de données sélectionnés pour le
  RGPD par détection de motifs (règles/expressions déterministes), sans appel LLM, afin
  d'identifier les catégories de données personnelles suivantes : identité, contact, identifiant
  national, santé, biométrie, origine/croyances.
- **FR-010a**: Lorsqu'une détection RGPD est reportée dans le rapport final, le système NE DOIT
  JAMAIS reproduire la valeur complète de la donnée personnelle détectée ; il DOIT présenter un
  extrait tronqué/masqué (ex. "j***@***.com") servant de preuve, conformément au principe de
  minimisation des données.
- **FR-011**: Le système DOIT combiner les résultats de l'analyse AI Act et de la détection RGPD
  en un profil de projet structuré unique, exploitable par les étapes en aval (hors scope de
  cette spec).
- **FR-012**: Le système DOIT générer un rapport final en langage clair, destiné à un lecteur non
  technique, citant les articles et annexes légaux (AI Act, RGPD) pertinents pour les éléments
  détectés, et DOIT l'afficher sous forme de page HTML structurée (sections, titres, listes)
  plutôt qu'en texte brut.
- **FR-013**: Le système NE DOIT JAMAIS citer, dans le rapport final, une référence légale
  (article, annexe) qui n'est pas présente dans le corpus de référence juridique fourni au
  système ; en l'absence de référence disponible pour un point donné, le rapport DOIT le signaler
  explicitement plutôt que d'inventer une citation.
- **FR-014**: Le système NE DOIT JAMAIS utiliser une réponse du LLM pour déterminer directement un
  niveau de risque de conformité ; cette classification reste la responsabilité d'un moteur de
  règles déterministe distinct, hors scope de cette spec.
- **FR-015**: Le système DOIT exposer, pour chaque évaluation, le nombre d'appels LLM effectués et
  la taille de contenu envoyée à chaque appel, afin de permettre le suivi du budget.
- **FR-016**: Le système DOIT gérer explicitement les cas d'échec (dépôt introuvable ou privé,
  limitation de débit de l'API GitHub, réponse LLM invalide ou inexploitable) en renvoyant un
  message d'erreur clair plutôt qu'un plantage silencieux ou un résultat partiel non signalé.
- **FR-017**: Le système NE DOIT PAS persister le rapport final, le contenu des fichiers analysés,
  ni les extraits de données personnelles détectés au-delà de la durée de traitement de la
  requête ; le rapport n'est renvoyé qu'à l'utilisateur ayant soumis la demande, sans stockage
  côté serveur au-delà de la réponse.

### Key Entities *(include if feature involves data)*

- **Dépôt cible**: Le dépôt GitHub public soumis pour évaluation ; identifié par son URL,
  caractérisé par son propriétaire, son nom, et sa visibilité (doit être publique).
- **Fichier du dépôt**: Un chemin de fichier listé dans le dépôt, avec ses métadonnées
  disponibles sans téléchargement du contenu (chemin, taille si disponible, extension).
- **Sélection AI Act**: Le sous-ensemble borné de fichiers du dépôt jugés pertinents pour
  l'analyse AI Act, avec leur contenu.
- **Sélection RGPD**: Le sous-ensemble borné de fichiers du dépôt jugés pertinents pour la
  détection RGPD, avec leur contenu.
- **Profil AI Act**: Le résultat structuré de l'analyse par LLM — secteur d'activité, finalité,
  niveau d'autonomie décisionnelle — accompagné des fichiers source ayant servi à la déduction.
- **Détection RGPD**: Une catégorie de donnée personnelle détectée (identité, contact,
  identifiant national, santé, biométrie, origine/croyances), associée au fichier source, au
  motif ayant déclenché la détection, et à un extrait tronqué/masqué de la valeur trouvée (jamais
  la valeur complète) servant de preuve.
- **Profil de projet combiné**: La fusion structurée du profil AI Act et des détections RGPD pour
  un dépôt donné, servant de base au rapport final et à toute classification de risque en aval.
- **Corpus juridique de référence**: L'ensemble des articles et annexes légaux (AI Act, RGPD)
  connus du système, seule source légitime de citation dans le rapport final.
- **Rapport final**: Le document en langage clair, rendu en page HTML structurée, produit pour
  l'utilisateur et affiché dans son navigateur, présentant le profil de projet combiné et les
  citations légales associées ; non persisté au-delà de la durée de traitement de la requête.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pour un dépôt GitHub public de taille courante (moins de 1000 fichiers), un rapport
  de conformité complet est produit en moins de 3 minutes.
- **SC-002**: 100% des évaluations effectuées respectent la limite de 2 appels LLM maximum,
  vérifiable via les journaux/compteurs exposés par le système.
- **SC-003**: 100% des références légales présentes dans un échantillon d'audit de rapports
  générés correspondent à une entrée existante du corpus juridique de référence (aucune
  référence inventée détectée).
- **SC-004**: Le coût LLM cumulé sur 100 évaluations reste sous le budget total de 10€ alloué au
  projet.
- **SC-005**: Sur un jeu de test de fichiers de données contenant des motifs représentatifs de
  chacune des 6 catégories de données personnelles visées, au moins 90% des occurrences connues
  sont détectées correctement.
- **SC-006**: 100% des tentatives d'évaluation sur un dépôt privé ou inexistant sont rejetées avec
  un message d'erreur clair, sans qu'aucun appel LLM ne soit déclenché.

## Assumptions

- Le moteur de règles déterministe qui transforme le profil de projet combiné en niveau de risque
  de conformité est hors scope de cette spec (confirmé explicitement par le commanditaire) ; le
  profil de projet combiné est le livrable final en aval duquel ce moteur pourra se brancher.
- La limite de sélection est fixée à 15 fichiers maximum par catégorie (AI Act et RGPD), et le
  plafond de contenu par appel LLM à 40 000 caractères ; ces valeurs sont des points de
  configuration révisables mais servent de référence pour le dimensionnement initial et le
  respect du budget de 10€ / 2 appels LLM par évaluation.
- Le corpus juridique de référence (textes AI Act et RGPD servant de source de citation) est une
  ressource déjà disponible ou fournie séparément au système ; la constitution de ce corpus
  elle-même est hors scope de cette spec, qui se limite à garantir qu'aucune citation ne sort de
  ce corpus.
- La liste des fichiers du dépôt est récupérée via l'API GitHub publique non authentifiée, avec
  les limites de débit associées à ce mode d'accès.
- Une évaluation traite un seul dépôt à la fois et produit un seul rapport par évaluation.
- La détection RGPD par motifs s'appuie sur un ensemble de règles/expressions prédéfini et
  maintenu par le système, non fourni par l'utilisateur à chaque évaluation.
