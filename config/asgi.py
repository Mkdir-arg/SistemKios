"""
Punto de entrada ASGI (por compatibilidad). La app se sirve por WSGI: el tiempo real
no pasa por acá sino por Supabase Realtime (REQ-INF-006).
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
