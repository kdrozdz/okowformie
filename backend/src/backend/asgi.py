"""
ASGI config dla projektu `backend`.

Nieużywane w produkcji na tym etapie (gunicorn+WSGI, patrz `backend/Dockerfile`),
utrzymywane jako standardowy plik projektu Django na wypadek przyszłej potrzeby
(np. websockety).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_asgi_application()
