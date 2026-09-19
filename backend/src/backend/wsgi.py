"""
WSGI config dla projektu `backend`.

Używane przez `gunicorn` w produkcji (patrz `backend/Dockerfile`).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_wsgi_application()
