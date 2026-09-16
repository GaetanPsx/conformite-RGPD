# Feature Specification: Pipeline d'analyse de conformité (dépôt GitHub ou documentation de projet)

**Feature Branch**: `001-repo-compliance-pipeline`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Construire le pipeline d'extraction et d'analyse d'un dépôt GitHub public ou d'une documentation de projet fournie directement, pour évaluer sa conformité AI Act et RGPD, avec récupération des références légales par RAG et production d'une liste de non-conformités, restituée dans un rapport téléchargeable et non persisté."

## Clarifications

### Session 2026-09-16

- Q: Quand une catégorie de donnée personnelle est détectée dans un fichier, le rapport doit-il inclure l'extrait de texte réellement trouvé, ou seulement signaler la catégorie et sa localisation sans reproduire la donnée elle-même ? → A: Catégorie + extrait tronqué/masqué (ex. "j***@***.com") à titre de preuve, sans exposer la donnée complète.
- Q: Comment l'utilisateur soumet-il l'URL du dépôt et reçoit-il le rapport final ? → A: Via une interface web (formulaire de saisie de l'URL, affichage du rapport dans le navigateur).
- Q: Au-delà de "README et manifeste de dépendances en premier", quelle règle complète détermine l'ordre de priorité pour choisir les fichiers restants au-delà de la limite de 15 par catégorie ? → A: Profondeur de chemin croissante (racine d'abord) puis ordre alphabétique du chemin complet.
- Q: Le rapport généré (et les extraits de données détectés) doit-il être conservé par le système après affichage à l'utilisateur, ou est-il éphémère ? → A: Éphémère, non persisté — le rapport n'est conservé que le temps de la requête/session et n'est pas écrit en base de données ou sur disque au-delà de la réponse renvoyée au navigateur.
- Q: Dans quel format le rapport doit-il être affiché sur l'interface web ? → A: HTML structuré (sections, titres, listes), adapté à un lecteur non technique.

### Session 2026-09-16 (amendement — RAG, second mode d'entrée, non-conformités, téléchargement)

- Q: En plus d'une URL de dépôt GitHub, quel second mode d'entrée le système doit-il accepter ? → A: De la documentation de projet fournie directement par l'utilisateur (texte collé ou fichier téléversé — README, spec, doc technique), sans dépôt Git associé ; le mode est déterminé automatiquement selon ce que l'utilisateur soumet (URL GitHub valide → mode dépôt ; texte/fichier fourni → mode documentation).
- Q: Comment les citations légales du rapport doivent-elles être obtenues ? → A: Par un composant de recherche (RAG) qui indexe localement le corpus juridique de référence et récupère, pour chaque évaluation, les passages les plus pertinents ; le rapport ne cite que des passages effectivement récupérés par cette recherche, jamais une référence choisie autrement.
- Q: La production d'une liste de non-conformités potentielles fait-elle partie du scope de cette spec ? → A: Oui, réintégrée au scope : chaque non-conformité listée doit être rattachée à un passage légal effectivement récupéré par le RAG. Le calcul d'un score ou niveau de risque global agrégé reste hors scope.
- Q: Le rapport doit-il rester uniquement affiché à l'écran ou aussi téléchargeable ? → A: Téléchargeable par l'utilisateur (export généré à la volée dans la réponse HTTP), en plus de l'affichage dans le navigateur, sans que cela remette en cause la non-persistance côté serveur.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtenir un rapport de conformité à partir d'un dépôt GitHub ou d'une documentation fournie (Priority: P1)

En tant qu'utilisateur (développeur, product owner, DPO), je soumets, via une interface web,
soit l'URL d'un dépôt GitHub public, soit directement de la documentation de mon projet (texte
collé ou fichier), et j'obtiens en retour, affiché dans mon navigateur, un rapport de conformité
en langage clair, couvrant à la fois l'AI Act et le RGPD, citant les articles/annexes légaux
pertinents, sans avoir à lire moi-même tout le code ou toute la documentation.

**Why this priority**: C'est la valeur centrale du produit — sans cette capacité de bout en bout,
sur au moins un des deux modes d'entrée, il n'y a pas de produit utilisable.

**Independent Test**: Soumettre l'URL d'un dépôt public réel contenant à la fois du code
d'inférence/modèle et des fichiers de données, et vérifier qu'un rapport structuré est produit,
contenant un profil AI Act, une liste de catégories de données personnelles détectées, et des
citations légales. Séparément, soumettre un texte de documentation collé décrivant un système
similaire et vérifier qu'un rapport équivalent est produit sans qu'aucun appel à l'API GitHub
n'ait lieu.

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
4. **Given** un texte de documentation de projet collé directement par l'utilisateur (sans URL de
   dépôt), **When** l'utilisateur lance une évaluation, **Then** le système traite ce texte comme
   contenu source sans appeler l'API GitHub, et produit un rapport de structure équivalente à
   celle obtenue en mode dépôt.
5. **Given** un fichier de documentation téléversé par l'utilisateur, **When** l'utilisateur lance
   une évaluation, **Then** le système utilise le contenu de ce fichier comme source unique
   d'analyse.
6. **Given** une soumission ne contenant ni URL de dépôt GitHub valide ni texte/fichier de
   documentation, **When** l'utilisateur tente de lancer une évaluation, **Then** le système
   rejette la demande avec un message clair indiquant qu'une des deux entrées est requise.

---

### User Story 2 - Recevoir une liste de non-conformités justifiées par des références légales retrouvées (Priority: P1)

En tant qu'utilisateur, je veux que le rapport m'indique, en langage clair, une liste de points de
non-conformité potentiels détectés pour mon projet, chacun rattaché à une référence légale AI Act
ou RGPD effectivement retrouvée par le système (et non choisie arbitrairement), afin de savoir
concrètement sur quoi agir.

**Why this priority**: C'est le livrable qui transforme un simple profil de données en résultat
actionnable ; sans cette liste, l'utilisateur devrait interpréter lui-même le profil brut, ce qui
annule une grande partie de la valeur de l'outil.

**Independent Test**: Soumettre un dépôt ou une documentation présentant des caractéristiques
connues de non-conformité potentielle (ex. absence de mention de base légale pour un traitement de
données de santé) et vérifier que le rapport produit une entrée de non-conformité mentionnant
explicitement ce point, avec une référence légale précise correspondant à un passage réellement
récupéré par le composant de recherche pour cette évaluation.

**Acceptance Scenarios**:

1. **Given** un profil de projet combiné (résultat AI Act + détections RGPD) pour une évaluation,
   **When** le rapport final est généré, **Then** il contient une section listant chaque point de
   non-conformité potentiel identifié, en langage clair, avec la référence légale associée.
2. **Given** un point de non-conformité présent dans le rapport, **When** on vérifie sa référence
   légale associée, **Then** cette référence correspond à un passage effectivement récupéré par la
   recherche légale (RAG) pour cette évaluation précise, et non à une référence choisie hors de ce
   contexte.
3. **Given** une évaluation pour laquelle aucun point de non-conformité n'est identifié,
   **When** le rapport est généré, **Then** il l'indique explicitement plutôt que d'omettre la
   section ou d'inventer un point.
4. **Given** un profil de projet pour lequel le corpus juridique ne contient aucun passage
   suffisamment pertinent pour un aspect détecté, **When** le rapport est généré, **Then** cet
   aspect n'est pas transformé en non-conformité non justifiée ; le système signale l'absence de
   référence disponible pour ce point plutôt que d'inventer une citation.

---

### User Story 3 - Respecter un budget d'appels LLM strict (Priority: P2)

En tant qu'utilisateur responsable du budget du projet, je veux que chaque évaluation respecte
une limite stricte d'appels LLM et de taille de contenu envoyée, afin que le coût par évaluation
reste prévisible et compatible avec un budget total de 10€ pour l'ensemble du projet.

**Why this priority**: Le budget LLM est une contrainte dure explicitement posée par le
commanditaire ; la dépasser rend le produit inutilisable en pratique, même si le reste
fonctionne.

**Independent Test**: Exécuter une évaluation sur un dépôt volumineux (des centaines de
fichiers) et vérifier, via les journaux/compteurs exposés par le système, qu'au maximum 2 appels
LLM sont effectués au total et qu'aucun appel n'envoie un contenu dépassant le plafond de taille
configuré. Vérifier également que la recherche de passages légaux (RAG) ne déclenche aucun appel
LLM supplémentaire.

**Acceptance Scenarios**:

1. **Given** un dépôt contenant plus de fichiers pertinents que la limite configurée,
   **When** le système sélectionne les fichiers pour l'analyse AI Act, **Then** il ne retient
   qu'un sous-ensemble borné par la limite, choisi selon une règle de priorité déterministe.
2. **Given** une évaluation complète d'un dépôt ou d'une documentation fournie, **When**
   l'évaluation se termine, **Then** le nombre total d'appels LLM effectués (y compris pour la
   génération de la liste de non-conformités) est au maximum 2, et ce nombre est visible dans le
   résultat ou les journaux de l'évaluation.
3. **Given** un fichier sélectionné ou une documentation fournie dont le contenu dépasse le
   plafond de taille par appel, **When** ce contenu est inclus dans l'envoi au LLM, **Then** il
   est tronqué ou exclu avant l'envoi, de façon à respecter le plafond.
4. **Given** une recherche de passages légaux pertinents pour une évaluation, **When** cette
   recherche s'exécute, **Then** elle ne déclenche aucun appel LLM (recherche locale déterministe
   uniquement).

---

### User Story 4 - Détecter les données personnelles sans appel LLM (Priority: P3)

En tant qu'utilisateur, je veux que la détection des catégories de données personnelles dans les
fichiers de données (ou la documentation fournie) soit effectuée uniquement par détection de
motifs (sans appel à un LLM), afin de garantir un coût nul, une exécution rapide et un résultat
reproductible pour cette partie de l'analyse.

**Why this priority**: C'est une contrainte de conception explicite qui conditionne le budget et
la fiabilité de la partie RGPD ; elle est indépendante de la partie AI Act et peut être livrée et
testée seule.

**Independent Test**: Fournir un dépôt ou un texte de documentation de test contenant des motifs
connus (adresses e-mail, numéros de sécurité sociale, identifiants de santé, etc.) et vérifier
que les catégories correspondantes sont détectées correctement, sans qu'aucun appel LLM ne soit
déclenché pendant cette étape.

**Acceptance Scenarios**:

1. **Given** un fichier de données (ou une documentation) contenant un motif reconnu
   d'identifiant national, **When** le scan RGPD s'exécute, **Then** la catégorie "identifiant
   national" est reportée avec sa source, sans qu'aucun appel LLM ne soit effectué pour cette
   détection.
2. **Given** un contenu ne contenant aucun motif de données personnelles connu, **When** le scan
   RGPD s'exécute, **Then** aucune catégorie n'est reportée pour ce contenu et le système ne
   signale pas de faux positif.

---

### User Story 5 - Télécharger le rapport généré (Priority: P3)

En tant qu'utilisateur, je veux pouvoir télécharger le rapport de conformité affiché dans mon
navigateur, afin de le conserver ou de le partager moi-même, sans que le système ne le stocke de
son côté.

**Why this priority**: C'est un complément direct à l'affichage du rapport, utile pour l'usage
réel du produit (partage, archivage par l'utilisateur), mais non bloquant pour la valeur centrale
déjà livrée par la consultation à l'écran.

**Independent Test**: Générer un rapport pour une évaluation, déclencher le téléchargement depuis
l'interface, et vérifier que le fichier obtenu contient l'intégralité du rapport affiché, et
qu'aucune trace de cette évaluation ne subsiste côté serveur après la réponse.

**Acceptance Scenarios**:

1. **Given** un rapport de conformité affiché dans le navigateur, **When** l'utilisateur déclenche
   le téléchargement, **Then** il obtient un fichier contenant l'intégralité du contenu du
   rapport (profil, détections RGPD, non-conformités, citations légales).
2. **Given** un téléchargement de rapport effectué, **When** on inspecte l'état du serveur après
   la réponse, **Then** aucune copie du rapport, du contenu analysé, ou des extraits détectés n'a
   été écrite en base de données ou sur disque.

---

### Edge Cases

- Que se passe-t-il si l'URL fournie pointe vers un dépôt privé, inexistant, ou n'est pas une URL
  GitHub valide, et qu'aucune documentation n'est fournie en alternative ? Le système doit rejeter
  la demande avec un message clair, sans déclencher d'appel LLM ni d'appel à l'API GitHub au-delà
  de la vérification d'accessibilité.
- Que se passe-t-il si l'utilisateur fournit à la fois une URL de dépôt et une documentation
  collée/téléversée dans la même soumission ? Le système doit appliquer une règle déterministe et
  documentée pour choisir un mode unique (voir Assumptions), plutôt que de mélanger silencieusement
  les deux sources.
- Que se passe-t-il si le texte de documentation fourni est vide, illisible, ou trop court pour
  produire une analyse pertinente ? Le système rejette la demande ou indique explicitement
  l'impossibilité d'analyser, sans inventer de résultat.
- Que se passe-t-il si le fichier téléversé n'est pas un format texte exploitable (ex. binaire) ?
  Il est rejeté avec un message clair avant tout appel LLM.
- Que se passe-t-il si le dépôt dépasse la limite de fichiers pertinents pour une ou les deux
  catégories (AI Act / RGPD) ? Le système sélectionne un sous-ensemble borné selon une règle de
  priorité déterministe et documente que la sélection est partielle.
- Que se passe-t-il si un fichier sélectionné est binaire, illisible en texte, ou dépasse la
  taille plafond à lui seul ? Il est exclu ou tronqué avant tout envoi au LLM ou scan de motifs.
- Que se passe-t-il si la réponse du LLM est malformée, vide, ou ne peut pas être interprétée ?
  Le système ne plante pas silencieusement ; le rapport final indique explicitement que l'analyse
  AI Act (et/ou la liste de non-conformités) a échoué pour cette évaluation.
- Que se passe-t-il en cas de limitation de débit (rate limiting) de l'API GitHub non
  authentifiée ? Le système renvoie un message d'erreur clair distinguant cette cause d'un dépôt
  invalide.
- Que se passe-t-il si aucune catégorie de données personnelles n'est détectée dans tout le
  dépôt ou toute la documentation ? Le rapport le mentionne explicitement plutôt que d'omettre
  silencieusement la section.
- Que se passe-t-il si la recherche légale (RAG) ne retrouve aucun passage pertinent pour un
  aspect du profil détecté ? Le rapport signale l'absence de référence disponible pour ce point
  plutôt que d'inventer une citation ou une non-conformité non justifiée.
- Que se passe-t-il si un article ou une annexe légale pertinent n'existe pas dans le corpus
  fourni ? Le rapport ne doit jamais inventer de référence ; il peut signaler l'absence de
  référence disponible pour ce point.
- Que se passe-t-il si le téléchargement du rapport est déclenché après expiration de la session
  ou de la requête ayant produit le rapport ? Le système doit indiquer clairement que le rapport
  n'est plus disponible (non persisté) plutôt que de renvoyer un fichier vide ou une erreur
  générique.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système DOIT permettre à un utilisateur de fournir, via une interface web, soit
  une URL de dépôt GitHub, soit de la documentation de projet fournie directement (texte collé ou
  fichier téléversé), et DOIT déterminer automatiquement le mode d'entrée (dépôt ou documentation)
  à partir de ce qui est soumis, en validant que l'entrée choisie correspond au format attendu
  (URL GitHub valide, ou contenu texte non vide) avant de poursuivre.
- **FR-001a**: Le système DOIT afficher le rapport final dans le navigateur de l'utilisateur, sur
  la même interface web ayant servi à la soumission.
- **FR-001b**: Le système DOIT permettre à l'utilisateur de télécharger le rapport final généré,
  en plus de son affichage dans le navigateur.
- **FR-002**: En mode dépôt, le système DOIT vérifier que le dépôt visé est public et accessible
  sans authentification, et DOIT rejeter clairement toute demande portant sur un dépôt privé ou
  inaccessible, sans mettre en œuvre de flux d'authentification OAuth.
- **FR-002a**: En mode documentation, le système NE DOIT PAS effectuer d'appel à l'API GitHub ; le
  contenu fourni directement (texte collé ou fichier) est utilisé comme unique source d'analyse.
- **FR-003**: En mode dépôt, le système DOIT récupérer la liste des chemins de fichiers du dépôt
  sans télécharger le contenu de ces fichiers à cette étape.
- **FR-004**: En mode dépôt, le système DOIT identifier, parmi la liste des fichiers, ceux
  pertinents pour l'AI Act (au minimum : README, fichiers de dépendances, code
  d'inférence/modèle).
- **FR-005**: En mode dépôt, le système DOIT identifier, parmi la liste des fichiers, ceux
  pertinents pour le RGPD (au minimum : schémas SQL, fichiers de migration, fixtures, fichiers de
  configuration JSON).
- **FR-006**: En mode dépôt, le système DOIT limiter le nombre de fichiers sélectionnés pour
  analyse à un maximum de 15 fichiers pour l'AI Act et 15 fichiers pour le RGPD par évaluation, en
  choisissant les fichiers selon la règle de priorité déterministe suivante lorsque plus de
  fichiers pertinents existent : (1) README et manifeste de dépendances en premier, (2) puis les
  fichiers restants triés par profondeur de chemin croissante (racine d'abord), (3) puis, à
  profondeur égale, par ordre alphabétique du chemin complet.
- **FR-006a**: En mode documentation, le contenu fourni est utilisé directement comme contenu
  source pour l'analyse AI Act et, si pertinent, pour le scan RGPD, sans étape de sélection de
  fichiers ; si ce contenu dépasse le plafond de taille par appel LLM (FR-008), il DOIT être
  tronqué selon une règle déterministe documentée plutôt que de faire échouer l'évaluation.
- **FR-007**: Le système DOIT envoyer à un LLM, en un seul appel au maximum par évaluation, le
  contenu source pertinent pour l'AI Act (fichiers sélectionnés ou documentation fournie) ainsi
  que les passages légaux les plus pertinents récupérés par le composant de recherche légale
  (FR-018), afin d'en déduire le secteur d'activité, la finalité, le niveau d'autonomie
  décisionnelle du système analysé, et une liste de points de non-conformité potentiels rattachés
  chacun à un passage légal récupéré.
- **FR-008**: Le système DOIT plafonner la taille du contenu envoyé à chaque appel LLM à un
  maximum de 40 000 caractères au total (contenu source et passages légaux récupérés cumulés,
  tronqués si nécessaire pour respecter cette limite).
- **FR-009**: Le système DOIT garantir qu'une évaluation complète n'effectue jamais plus de 2
  appels LLM au total, tous usages confondus (y compris la génération de la liste de
  non-conformités).
- **FR-010**: Le système DOIT scanner le contenu des fichiers de données sélectionnés (ou de la
  documentation fournie) par détection de motifs (règles/expressions déterministes), sans appel
  LLM, afin d'identifier les catégories de données personnelles suivantes : identité, contact,
  identifiant national, santé, biométrie, origine/croyances.
- **FR-010a**: Lorsqu'une détection RGPD est reportée dans le rapport final, le système NE DOIT
  JAMAIS reproduire la valeur complète de la donnée personnelle détectée ; il DOIT présenter un
  extrait tronqué/masqué (ex. "j***@***.com") servant de preuve, conformément au principe de
  minimisation des données.
- **FR-011**: Le système DOIT combiner les résultats de l'analyse AI Act, de la détection RGPD, et
  de la liste de points de non-conformité en un profil de projet structuré unique, exploitable par
  les étapes en aval (hors scope de cette spec).
- **FR-012**: Le système DOIT générer un rapport final en langage clair, destiné à un lecteur non
  technique, citant les articles et annexes légaux (AI Act, RGPD) pertinents pour les éléments
  détectés, incluant une section listant les points de non-conformité potentiels identifiés
  (ou l'absence explicite de tout point identifié), et DOIT l'afficher sous forme de page HTML
  structurée (sections, titres, listes) plutôt qu'en texte brut.
- **FR-013**: Le système NE DOIT JAMAIS citer, dans le rapport final (profil AI Act ou liste de
  non-conformités), une référence légale (article, annexe) qui n'a pas été effectivement récupérée
  par le composant de recherche légale (FR-018) pour cette évaluation ; en l'absence de passage
  pertinent récupéré pour un point donné, le rapport DOIT le signaler explicitement plutôt que
  d'inventer une citation ou un point de non-conformité non justifié.
- **FR-014**: Le système NE DOIT JAMAIS utiliser une réponse du LLM pour déterminer directement un
  score ou niveau de risque de conformité global ; cette classification agrégée reste la
  responsabilité d'un moteur de règles déterministe distinct, hors scope de cette spec. La liste
  de points de non-conformité individuels (FR-007, FR-012), elle, est dans le scope de cette spec.
- **FR-015**: Le système DOIT exposer, pour chaque évaluation, le nombre d'appels LLM effectués et
  la taille de contenu envoyée à chaque appel, afin de permettre le suivi du budget.
- **FR-016**: Le système DOIT gérer explicitement les cas d'échec (dépôt introuvable ou privé,
  documentation vide ou illisible, limitation de débit de l'API GitHub, réponse LLM invalide ou
  inexploitable) en renvoyant un message d'erreur clair plutôt qu'un plantage silencieux ou un
  résultat partiel non signalé.
- **FR-017**: Le système NE DOIT PAS persister le rapport final, le contenu source analysé
  (fichiers de dépôt ou documentation fournie), ni les extraits de données personnelles détectés
  au-delà de la durée de traitement de la requête ; le rapport (affiché et/ou téléchargé) n'est
  renvoyé qu'à l'utilisateur ayant soumis la demande, sans stockage côté serveur au-delà de la
  réponse HTTP.
- **FR-018**: Le système DOIT maintenir un index de recherche local du corpus juridique de
  référence (AI Act, RGPD), construit et interrogé sans aucun appel LLM, permettant de récupérer,
  pour un profil ou un contenu source donné, un ensemble borné des passages légaux les plus
  pertinents.
- **FR-019**: Pour chaque évaluation, le système DOIT interroger cet index et transmettre les
  passages récupérés au LLM (FR-007) ; seuls ces passages effectivement récupérés pour cette
  évaluation peuvent être cités dans le rapport final (profil AI Act ou liste de
  non-conformités).

### Key Entities *(include if feature involves data)*

- **Dépôt cible**: Le dépôt GitHub public soumis pour évaluation (mode dépôt) ; identifié par son
  URL, caractérisé par son propriétaire, son nom, et sa visibilité (doit être publique).
- **Documentation fournie**: Le contenu de documentation de projet soumis directement par
  l'utilisateur en alternative à un dépôt (mode documentation) — texte collé ou fichier téléversé
  — utilisé comme unique source d'analyse pour cette évaluation.
- **Fichier du dépôt**: Un chemin de fichier listé dans le dépôt, avec ses métadonnées
  disponibles sans téléchargement du contenu (chemin, taille si disponible, extension).
- **Sélection AI Act**: Le sous-ensemble borné de fichiers du dépôt (ou le contenu de
  documentation fourni) jugé pertinent pour l'analyse AI Act, avec son contenu.
- **Sélection RGPD**: Le sous-ensemble borné de fichiers du dépôt (ou le contenu de documentation
  fourni) jugé pertinent pour la détection RGPD, avec son contenu.
- **Corpus juridique de référence**: L'ensemble des articles et annexes légaux (AI Act, RGPD)
  connus du système, indexé localement pour permettre une recherche de passages pertinents
  (composant RAG) ; seule source légitime de passages citables dans le rapport final.
- **Passage légal récupéré**: Un extrait du corpus juridique de référence, retourné par le
  composant de recherche légale pour une évaluation donnée, associé à un score de pertinence et à
  sa référence (article/annexe) ; seule unité citable dans le rapport pour cette évaluation.
- **Profil AI Act**: Le résultat structuré de l'analyse par LLM — secteur d'activité, finalité,
  niveau d'autonomie décisionnelle — accompagné des fichiers/contenu source ayant servi à la
  déduction et des passages légaux récupérés utilisés.
- **Détection RGPD**: Une catégorie de donnée personnelle détectée (identité, contact,
  identifiant national, santé, biométrie, origine/croyances), associée à la source (fichier ou
  documentation), au motif ayant déclenché la détection, et à un extrait tronqué/masqué de la
  valeur trouvée (jamais la valeur complète) servant de preuve.
- **Non-conformité potentielle**: Un point signalé dans le rapport, en langage clair, décrivant un
  écart potentiel de conformité identifié à partir du profil de projet combiné, rattaché à un
  passage légal récupéré précis.
- **Profil de projet combiné**: La fusion structurée du profil AI Act, des détections RGPD, et de
  la liste de non-conformités potentielles pour une évaluation donnée, servant de base au rapport
  final et à toute classification de risque agrégée en aval.
- **Rapport final**: Le document en langage clair, rendu en page HTML structurée, produit pour
  l'utilisateur, affiché dans son navigateur et téléchargeable par lui, présentant le profil de
  projet combiné et les citations légales associées ; non persisté au-delà de la durée de
  traitement de la requête.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pour un dépôt GitHub public de taille courante (moins de 1000 fichiers) ou une
  documentation fournie directement, un rapport de conformité complet est produit en moins de 3
  minutes.
- **SC-002**: 100% des évaluations effectuées respectent la limite de 2 appels LLM maximum,
  vérifiable via les journaux/compteurs exposés par le système.
- **SC-003**: 100% des références légales présentes dans un échantillon d'audit de rapports
  générés (profil AI Act et liste de non-conformités) correspondent à un passage effectivement
  récupéré par la recherche légale pour l'évaluation concernée (aucune référence inventée ou hors
  contexte détectée).
- **SC-004**: Le coût LLM cumulé sur 100 évaluations reste sous le budget total de 10€ alloué au
  projet.
- **SC-005**: Sur un jeu de test de fichiers/documentations contenant des motifs représentatifs de
  chacune des 6 catégories de données personnelles visées, au moins 90% des occurrences connues
  sont détectées correctement.
- **SC-006**: 100% des tentatives d'évaluation sur un dépôt privé ou inexistant, sans
  documentation alternative fournie, sont rejetées avec un message d'erreur clair, sans qu'aucun
  appel LLM ne soit déclenché.
- **SC-007**: 100% des évaluations menées en soumettant une documentation de projet fournie
  directement (sans URL de dépôt) produisent un rapport sans qu'aucun appel à l'API GitHub ne soit
  effectué.
- **SC-008**: Sur un échantillon d'audit de rapports générés, chaque évaluation ayant identifié au
  moins un point de non-conformité potentiel présente ce point associé à une référence légale
  précise et vérifiable dans le corpus de référence.
- **SC-009**: 100% des rapports affichés peuvent être téléchargés par l'utilisateur en un clic
  depuis l'interface, et aucune trace du rapport ou de son contenu source n'est retrouvée côté
  serveur après la fin du traitement de la requête correspondante.

## Assumptions

- Le moteur de règles déterministe qui transforme le profil de projet combiné en score ou niveau
  de risque de conformité **global agrégé** est hors scope de cette spec (confirmé explicitement
  par le commanditaire) ; en revanche, la production de la liste de points de non-conformité
  individuels, chacun rattaché à une référence légale récupérée, est dans le scope de cette spec.
- La limite de sélection est fixée à 15 fichiers maximum par catégorie (AI Act et RGPD) en mode
  dépôt, et le plafond de contenu par appel LLM à 40 000 caractères ; ces valeurs sont des points
  de configuration révisables mais servent de référence pour le dimensionnement initial et le
  respect du budget de 10€ / 2 appels LLM par évaluation.
- Le corpus juridique de référence (textes AI Act et RGPD servant de source de citation) est une
  ressource déjà disponible ou fournie séparément au système ; la constitution de ce corpus
  elle-même est hors scope de cette spec, qui se limite à garantir qu'aucune citation ne sort des
  passages effectivement récupérés par la recherche (RAG) sur ce corpus.
- La méthode d'indexation/recherche locale du corpus (embeddings pré-calculés, recherche lexicale
  de type BM25/TF-IDF, ou une combinaison) est un détail d'implémentation laissé au plan technique
  ; la seule contrainte de spec est qu'elle soit déterministe et n'entraîne aucun appel LLM.
- La liste des fichiers du dépôt est récupérée via l'API GitHub publique non authentifiée, avec
  les limites de débit associées à ce mode d'accès ; cette contrainte ne s'applique pas au mode
  documentation.
- Si un utilisateur fournit à la fois une URL de dépôt et une documentation dans la même
  soumission, le système privilégie le mode dépôt et ignore la documentation fournie en parallèle,
  en le signalant à l'utilisateur ; ce choix est un point de configuration révisable.
- Une évaluation traite une seule source (un dépôt ou une documentation) à la fois et produit un
  seul rapport par évaluation.
- La détection RGPD par motifs s'appuie sur un ensemble de règles/expressions prédéfini et
  maintenu par le système, non fourni par l'utilisateur à chaque évaluation.
- Le format de téléchargement du rapport est, par défaut, le même document HTML structuré que
  celui affiché dans le navigateur (export du rendu existant plutôt qu'un format additionnel type
  PDF), ce format pouvant évoluer sans changement de cette spec tant que FR-001b et FR-017 restent
  respectés.
