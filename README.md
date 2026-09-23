# conformite-RGPD

Pipeline d'analyse de conformité AI Act / RGPD à partir d'un dépôt GitHub public ou d'une
documentation de projet fournie directement. Application web FastAPI + Jinja2, sans persistance
serveur : un rapport HTML est généré par requête et peut être téléchargé (voir
[specs/001-repo-compliance-pipeline/spec.md](specs/001-repo-compliance-pipeline/spec.md)).

## Prérequis

- Python 3.11+
- Une clé API OpenAI valide (`OPENAI_API_KEY`), utilisée pour l'unique appel LLM payant par
  évaluation
- Accès réseau sortant vers `api.github.com` (non authentifié, uniquement en mode dépôt)

## Installation locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Recherche légale (RAG)

Le corpus juridique (`src/data/legal_corpus/corpus.json`, une dizaine de passages) est indexé en
mémoire au démarrage (TF-IDF, numpy) : aucune étape de build ni modèle d'embedding à embarquer.
Pour enrichir le corpus, il suffit d'éditer `corpus.json`.

## Lancer le service localement

```bash
export OPENAI_API_KEY=sk-...
uvicorn src.web.app:app --reload
```

Puis ouvrir `http://localhost:8000/`.

## Lancer les tests

```bash
pip install -r requirements.txt
python -m pytest
```

Les tests d'intégration et de contrat simulent les appels GitHub et OpenAI via `respx` : aucun
appel réseau réel ni clé API valide n'est nécessaire pour les faire passer.

## Déploiement (Azure App Service)

L'application est hébergée sur Azure App Service (Linux), sous le nom `rgpd-conformite-64879`
(`https://rgpd-conformite-64879.azurewebsites.net`). Le déploiement se fait par build de code
Python géré par Azure (Oryx, à partir de `requirements.txt`), pas par image conteneur.

Déploiement continu : le workflow GitHub Actions
[.github/workflows/deploy.yml](.github/workflows/deploy.yml) déploie automatiquement sur Azure à
chaque push sur `main`, via l'action `azure/webapps-deploy@v3` et le secret de dépôt
`AZURE_WEBAPP_PUBLISH_PROFILE` (profil de publication téléchargé depuis le portail Azure : Web App
→ *Get publish profile*, à stocker dans *Settings → Secrets and variables → Actions*).

Configuration requise côté Azure (Web App → *Configuration → Application settings*) :

- `OPENAI_API_KEY` : la clé API OpenAI, jamais committée en clair dans le dépôt.
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true` (généralement activé par défaut pour un déploiement Python
  via `webapps-deploy`) afin qu'Azure installe `requirements.txt` pendant le déploiement.
- Un tier App Service Linux `B1` recommandé, avec *Always On* activé pour éviter la mise en veille
  (et donc un démarrage à froid).

La CI (`.github/workflows/tests.yml`) exécute la suite `pytest` sur chaque push/PR avant tout
déploiement.

## Déploiement (Vercel)

Le dépôt est aussi déployable sur Vercel : [app.py](app.py) (à la racine) expose l'application
FastAPI, [vercel.json](vercel.json) règle la durée maximale de la fonction (30 s) et
`.vercelignore` exclut tests, specs et outils de dev du bundle. Seul `requirements.txt` (dépendances
d'exécution) est installé ; les dépendances de test sont dans `requirements-dev.txt`.

Variable d'environnement à définir dans Vercel (*Settings → Environment Variables*) :
`OPENAI_API_KEY`. Le rate limiting par IP est en mémoire : il ne s'applique donc que par instance
serverless.
