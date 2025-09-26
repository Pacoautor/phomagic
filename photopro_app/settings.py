# photopro_app/settings.py
from pathlib import Path
import os
import dj_database_url

# ========================
# Rutas base
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# Seguridad
# ========================
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = True

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "phomagic-web.onrender.com,phomagic.com,www.phomagic.com,127.0.0.1,localhost"
).split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://phomagic-web.onrender.com",
    "https://phomagic.com",
    "https://www.phomagic.com",
]

# ========================
# Apps
# ========================
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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "photopro_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "photopro_app.wsgi.application"

# ========================
# Base de datos
# ========================
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ========================
# Internacionalización
# ========================
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# ========================
# --- Archivos estáticos ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"     # destino de collectstatic

# directorios de estáticos dentro del repo (aquí está products/static)
STATICFILES_DIRS = [
    BASE_DIR / "products" / "static",
]

# WhiteNoise para servir estáticos en producción
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # << debe ir justo tras SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Compresión/caché de estáticos
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- Archivos de usuario (media) ---
MEDIA_URL = "/media/"
# IMPORTANTE: pon aquí la ruta donde montaste el Disk de Render (ej.: /opt/render/project/media)
MEDIA_ROOT = BASE_DIR / "media"
