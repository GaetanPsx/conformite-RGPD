"""Point d'entree Vercel : expose l'application FastAPI sous le nom `app` (detecte a la racine).

En local ou sur Azure, l'application se lance toujours via `uvicorn src.web.app:app`.
"""

from src.web.app import app  # noqa: F401
