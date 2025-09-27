# photopro_app/settings.py
from pathlib import Path
import os
import dj_database_url

# ========================
# Rutas base
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# Seguridad / Entorno
# ========================
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "0") == "1"

# Puedes pasar ALLOWED_HOSTS desde el panel (separados por comas),
# o usamos estos valores por defecto:
ALLOWED_HOSTS = [
    "phomagic.com",
    "www.phomagic.com",
    "phomagic-web.onrender.com",
    "localhost",
    "127.0.0.1",
]
# Si hay var en entorno, la priorizamos
_env_hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if _env_hosts:
    ALLOWED_HOSTS = _env_hosts

CSRF_TRUSTED_ORIGINS = [
    "https://phomagic.com",
    "https://www.phomagic.com",
    "https://phomagic-web.onrender.com",
]
_env_csrf = [u.strip() for u in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if u.strip()]
if _env_csrf:
    CSRF_TRUSTED_ORIGINS = _env_csrf

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

    # Tu app
    "products",
]

# ========================
# Middleware
# ========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Debe ir justo detrás de SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ========================
# URLs / WSGI
# ========================
ROOT_URLCONF = "photopro_app.urls"
WSGI_APPLICATION = "photopro_app.wsgi.application"

# ========================
# Templates
# ========================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # carpeta 'templates' raíz (opcional)
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

# ========================
# Base de datos
# ========================
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=False,  # Render maneja SSL; mantenemos False para evitar problemas locales
        )
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
# Archivos estáticos
# ========================
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ...

DEBUG = False  # en producción mantenlo en False

ALLOWED_HOSTS = ["www.phomagic.com", "phomagic.com", "phomagic-web.onrender.com"]

# Static files (CSS, JS, imágenes)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "products" / "static",   # <- TU carpeta de estáticos del proyecto
]

# WhiteNoise
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # <- debe ir justo después de SecurityMiddleware
    # ... el resto de middlewares
]

# ⚠️ TEMPORAL para evitar 500 por ficheros estáticos faltantes:
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# (Cuando acabemos de corregir rutas, lo devolveremos a:)
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media (si usas MEDIA para resultados o subidas)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# ========================
# Archivos de usuario (media)
# ========================
# En Render, si montaste un Disk en /opt/render/project/media, úsalo vía env:
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

# ========================
# Login/Logout
# ========================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# ========================
# Auto IDs
# ========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ========================
# Seguridad extra en producción
# ========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24  # 1 día (sube cuando todo esté estable)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Logging: enviar errores de Django a la consola de Render ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Errores de vistas/respuestas -> a consola con traceback
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Si quieres algo más de ruido, puedes subir a WARNING o INFO
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

# Mostrar tracebacks completos de errores 500 en consola
import sys
LOGGING["handlers"]["console"]["stream"] = sys.stdout
LOGGING["loggers"]["django.request"]["level"] = "DEBUG"
LOGGING["loggers"]["django"]["level"] = "DEBUG"

