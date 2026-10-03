"""
Configuración de Django para SistemKios.

Se apoya en variables de entorno (ver .env.example) para no hardcodear
credenciales ni parámetros de despliegue.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)

# Lee un archivo .env si existe (útil en local; en Docker se pasan por env_file).
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)

# --- Núcleo -----------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="dev-inseguro-cambiar-en-produccion")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Propias
    "apps.core",
    "apps.puntos",
    "apps.accounts",
    "apps.catalogo",
    "apps.stock",
    "apps.caja",
    "apps.ventas",
    "apps.transferencias",
    "apps.ofertas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise sirve los estáticos fuera de Vercel (en Vercel los sirve su CDN).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Solo WSGI: el tiempo real lo sirve Supabase Realtime, no esta app (REQ-INF-006).
WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos ----------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://sistemkios:sistemkios@db:5432/sistemkios",
    )
}
_db = DATABASES["default"]
if "supabase" in (_db.get("HOST") or ""):
    _db.setdefault("OPTIONS", {})["sslmode"] = "require"
# Pooler de Supabase en modo transacción (puerto 6543), el que usa la app en Vercel: cada
# consulta puede caer en otra conexión, así que no hay conexiones persistentes ni cursores
# del lado del servidor.
if env.bool("DB_POOLER_TRANSACCION", default=str(_db.get("PORT")) == "6543"):
    _db["CONN_MAX_AGE"] = 0
    _db["DISABLE_SERVER_SIDE_CURSORS"] = True

# --- Supabase: tiempo real e imágenes ----------------------------------------
SUPABASE_URL = env("SUPABASE_URL", default="").rstrip("/")
# Clave pública (anon / publishable): viaja al navegador para conectarse a Realtime.
SUPABASE_ANON_KEY = env("SUPABASE_ANON_KEY", default="")
# Con qué firma Django los tokens de Realtime: una clave privada importada en Supabase
# (ES256/RS256, recomendado) o el JWT secret compartido (HS256).
# En una variable de entorno el PEM suele venir en una sola línea, con "\n" escritos.
SUPABASE_JWT_PRIVATE_KEY = env("SUPABASE_JWT_PRIVATE_KEY", default="").replace("\\n", "\n")
SUPABASE_JWT_KID = env("SUPABASE_JWT_KID", default="")
SUPABASE_JWT_SECRET = env("SUPABASE_JWT_SECRET", default="")
TIEMPO_REAL_HABILITADO = bool(
    SUPABASE_URL and SUPABASE_ANON_KEY and (SUPABASE_JWT_PRIVATE_KEY or SUPABASE_JWT_SECRET)
)

# --- Autenticación ----------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalización ---------------------------------------------------
LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos -----------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Archivos subidos por el usuario (imágenes de productos). En local van a disco; en
# producción, a Supabase Storage (ver más abajo): el disco de Vercel no persiste.
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # En producción: comprime y versiona (hash) los estáticos vía WhiteNoise.
        # En desarrollo: almacenamiento simple para que `runserver` los sirva directo.
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# Imágenes en Supabase Storage, por su API compatible con S3. El bucket es público:
# las imágenes se sirven directo desde Supabase, sin pasar por la app.
SUPABASE_S3_ACCESS_KEY = env("SUPABASE_S3_ACCESS_KEY", default="")
if SUPABASE_S3_ACCESS_KEY:
    _bucket = env("SUPABASE_BUCKET", default="media")
    _host = SUPABASE_URL.split("://", 1)[-1]
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": _bucket,
            "endpoint_url": f"{SUPABASE_URL}/storage/v1/s3",
            "access_key": SUPABASE_S3_ACCESS_KEY,
            "secret_key": env("SUPABASE_S3_SECRET_KEY"),
            "region_name": env("SUPABASE_S3_REGION", default="sa-east-1"),
            "addressing_style": "path",
            "custom_domain": f"{_host}/storage/v1/object/public/{_bucket}",
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Seguridad y despliegue --------------------------------------------------
# Vercel inyecta los dominios del deploy; se suman a los hosts y orígenes de confianza.
for _var in ("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL", "VERCEL_URL"):
    _dominio = env(_var, default="")
    if _dominio:
        if "*" not in ALLOWED_HOSTS:
            ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [_dominio]
        CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [f"https://{_dominio}"]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Vercel ya fuerza HTTPS en el borde: el redirect en la app va apagado por defecto.
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
