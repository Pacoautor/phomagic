import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# ----------------------------------------------------
# CARGA DE VARIABLES .ENV (si existe en local)
# ----------------------------------------------------
load_dotenv()

# ----------------------------------------------------
# RUTAS BASE
# ----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------------------------------
# CONFIGURACIÓN BÁSICA
# ----------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-this")
DEBUG = os.getenv("DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    "phomagic-web.onrender.com",
    "phomagic.com",
    "www.phomagic.com",
    "127.0.0.1",
    "localhost",
]

CSRF_TRUSTED_ORIGINS = [
    "https://phomagic-web.onrender.com",
    "https://phomagic.com",
    "https://www.phomagic.com",
]

# ----------------------------------------------------
# APLICACIONES
# ----------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "products",
    "catalog",  # <- añadido si tu aplicación usa categorías
]

# ----------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ----------------------------------------------------
# URLS Y WSGI
# ----------------------------------------------------
ROOT_URLCONF = "phomagic.urls"
WSGI_APPLICATION = "phomagic.wsgi.application"

# ----------------------------------------------------
# PLANTILLAS
# ----------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
            os.path.join(BASE_DIR, "products", "templates"),
        ],
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

# ----------------------------------------------------
# BASE DE DATOS
# ----------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# ----------------------------------------------------
# VALIDADORES DE CONTRASEÑA
# ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------------------------------
# INTERNACIONALIZACIÓN
# ----------------------------------------------------
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------
# ARCHIVOS ESTÁTICOS Y MEDIA
# ----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "products", "static")]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ----------------------------------------------------
# CONFIGURACIÓN OPENAI
# ----------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ----------------------------------------------------
# LOGGING — Mostrar errores 500 en consola (para Render)
# ----------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
}

# ----------------------------------------------------
# CONFIGURACIÓN DE SEGURIDAD (solo producción)
# ----------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ----------------------------------------------------
# CONFIGURACIÓN FINAL
# ----------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
