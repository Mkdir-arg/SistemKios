"""
Configuración de la base cuando corre en Supabase. En otro Postgres (local, tests) no
existen el esquema `realtime` ni los roles `anon`/`authenticated`, y no hace nada.

1. Cierra la Data API sobre las tablas de Django (REQ-INF-007). Supabase publica el esquema
   `public` por HTTP a los roles `anon` y `authenticated`, y la clave anon viaja al navegador
   (la usa Realtime). Sin esto, cualquiera con esa clave podría leer o escribir las tablas
   de la app, usuarios incluidos. Django se conecta como `postgres`, al que esto no afecta.
2. Política RLS de Realtime (REQ-RT-003): un token solo escucha los canales de su claim
   `sk_canales`, salvo que tenga `sk_admin`.
"""
from django.db import migrations

CERRAR_DATA_API = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
    REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
    -- Y las tablas que creen las migraciones futuras (las crea el rol con el que migra Django).
    EXECUTE format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated',
      current_user);
    EXECUTE format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated',
      current_user);
    EXECUTE format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated',
      current_user);
  END IF;
END $$;
"""

POLITICA_REALTIME = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'realtime')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    DROP POLICY IF EXISTS "sistemkios escucha sus puntos" ON realtime.messages;
    CREATE POLICY "sistemkios escucha sus puntos" ON realtime.messages
      FOR SELECT TO authenticated
      USING (
        realtime.messages.extension = 'broadcast'
        AND (
          coalesce((auth.jwt() ->> 'sk_admin')::boolean, false)
          OR (SELECT realtime.topic()) IN (
            SELECT jsonb_array_elements_text(coalesce(auth.jwt() -> 'sk_canales', '[]'::jsonb))
          )
        )
      );
  END IF;
END $$;
"""

SACAR_POLITICA = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'realtime') THEN
    DROP POLICY IF EXISTS "sistemkios escucha sus puntos" ON realtime.messages;
  END IF;
END $$;
"""


class Migration(migrations.Migration):

    # Después de que existan todas las tablas, para que el REVOKE las alcance.
    dependencies = [
        ("accounts", "0001_initial"),
        ("puntos", "0002_deposito"),
        ("catalogo", "0004_preciopunto_margen"),
        ("stock", "0001_initial"),
        ("caja", "0001_initial"),
        ("ventas", "0003_pagos_sin_vuelto"),
        ("transferencias", "0001_initial"),
        ("ofertas", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("sessions", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunSQL(CERRAR_DATA_API, migrations.RunSQL.noop),
        migrations.RunSQL(POLITICA_REALTIME, SACAR_POLITICA),
    ]
