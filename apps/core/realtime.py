"""
Tiempo real con Supabase Realtime (Broadcast en canales privados).

- Cada punto tiene un canal: `punto-{id}`.
- El servidor publica con `notificar_punto`, que llama a `realtime.send()` en la base de
  Supabase. Realtime lee la tabla por replicación y reenvía el mensaje a los conectados.
- El navegador se suscribe con supabase-js usando un token que firma Django
  (`token_para`): solo deja escuchar los canales que el usuario puede ver.
- Sin Supabase configurado (local, tests), no se publica nada y la pantalla lo muestra.
"""
import json
import logging
import time

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection

log = logging.getLogger(__name__)

# Duración de los tokens de Realtime. El cliente pide uno nuevo antes de que venza.
DURACION_TOKEN = 60 * 60


def canal_punto(punto_id):
    return f"punto-{punto_id}"


def notificar_punto(punto_id, tipo, **data):
    """
    Publica `{tipo, ...data}` en el canal del punto.

    Se llama dentro de `transaction.on_commit` (REQ-RT-002). Un error acá no puede romper
    la operación que ya se guardó: se registra y sigue.
    """
    if punto_id is None or not settings.TIEMPO_REAL_HABILITADO:
        return
    payload = json.dumps({"tipo": tipo, **data}, cls=DjangoJSONEncoder)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "select realtime.send(%s::jsonb, %s, %s, true)",
                [payload, tipo, canal_punto(punto_id)],
            )
    except Exception:
        log.exception("No se pudo publicar el evento %s del punto %s", tipo, punto_id)


def token_para(user):
    """
    Token para que el navegador de `user` se conecte a Realtime (REQ-RT-003).

    Es un JWT con rol `authenticated` y los canales permitidos en el claim `sk_canales`;
    la política RLS de `realtime.messages` (migración core/0001) solo deja escuchar esos.
    El Super Admin lleva `sk_admin` y puede escuchar cualquier punto.
    """
    import jwt

    ahora = int(time.time())
    claims = {
        "role": "authenticated",
        "aud": "authenticated",
        "sub": f"sistemkios-{user.pk}",
        "iat": ahora,
        "exp": ahora + DURACION_TOKEN,
        "sk_admin": bool(user.es_super_admin),
        "sk_canales": [canal_punto(user.punto_id)] if user.punto_id else [],
    }
    if settings.SUPABASE_JWT_PRIVATE_KEY:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        clave = load_pem_private_key(settings.SUPABASE_JWT_PRIVATE_KEY.encode(), password=None)
        algoritmo = "RS256" if isinstance(clave, rsa.RSAPrivateKey) else "ES256"
        headers = {"kid": settings.SUPABASE_JWT_KID} if settings.SUPABASE_JWT_KID else None
        return jwt.encode(claims, clave, algorithm=algoritmo, headers=headers)
    return jwt.encode(claims, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
