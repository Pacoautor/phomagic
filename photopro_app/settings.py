from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LINEAS_ROOT = MEDIA_ROOT / 'lineas'

# (Opcional: crea las carpetas si no existen)
for sub in ("uploads/input", "uploads/output", "uploads/tmp", "lineas"):
    (MEDIA_ROOT / sub).mkdir(parents=True, exist_ok=True)

ALLOWED_HOSTS = [
    "phomagic-web.onrender.com",
    "phomagic.com",
    "www.phomagic.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://phomagic-web.onrender.com",
    "https://phomagic.com",
    "https://www.phomagic.com",
]

SESSION_COOKIE_DOMAIN = ".phomagic.com"
CSRF_COOKIE_DOMAIN = ".phomagic.com"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "products",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "photopro_app.urls"
WSGI_APPLICATION = "photopro_app.wsgi.application"

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

def _use_data_disk() -> bool:
    return os.path.isdir("/data") and os.access("/data", os.W_OK)

db_path = "/data/db.sqlite3" if _use_data_disk() else str(BASE_DIR / "db.sqlite3")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": db_path}}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- Media: usar carpeta local del proyecto (persistencia no garantizada entre deploys) ---
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"   # <— en vez de /data/media

# Crea subcarpetas locales (sí es escribible)
for sub in ("uploads/input", "uploads/output", "uploads/tmp", "lineas"):
    (MEDIA_ROOT / sub).mkdir(parents=True, exist_ok=True)

# === Carpetas de trabajo ===
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Carpeta principal con categorías y vistas
LINEAS_ROOT = MEDIA_ROOT / 'lineas'

# Crear carpetas necesarias (solo si se puede escribir)
for sub in ("uploads/input", "uploads/output", "uploads/tmp", "lineas"):
    try:
        (MEDIA_ROOT / sub).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
