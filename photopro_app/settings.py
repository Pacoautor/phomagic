# photopro_app/settings.py
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / entorno ---
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Dominios (Render público)
ALLOWED_HOSTS = ["phomagic-web.onrender.com"] if not DEBUG else ["*"]
CSRF_TRUSTED_ORIGINS = ["https://phomagic-web.onrender.com"]

# Cookies seguras y cabeceras proxy
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "products",
]

# --- Middleware (WhiteNoise para estáticos) ---
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

# --- Templates ---
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"] if (BASE_DIR / "templates").exists() else [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# --- Base de datos (SQLite persistente en /data en prod) ---
DEFAULT_DB_PATH = "/data/db.sqlite3" if not DEBUG else str(BASE_DIR / "db.sqlite3")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DEFAULT_DB_PATH}}

# --- Estáticos y Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
local_static = BASE_DIR / "static"
STATICFILES_DIRS = [local_static] if local_static.exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/data/media"))
for sub in ("uploads/input", "uploads/output", "uploads/tmp"):
    try:
        (MEDIA_ROOT / sub).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# --- I18N ---
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Logging a consola (Render Logs) ---
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}

# --- Integraciones ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
