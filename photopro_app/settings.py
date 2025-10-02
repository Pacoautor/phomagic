# photopro_app/settings.py
from pathlib import Path
import os
import dj_database_url

# =======================
# Rutas base
# =======================
BASE_DIR = Path(__file__).resolve().parent.parent

# =======================
# Seguridad / Entorno
# =======================
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    "phomagic.com",
    "www.phomagic.com",
    "phomagic-web.onrender.com",
    "localhost",
    "127.0.0.1",
]
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
    CSRF_TRUSTED_ORIGINS.extend([u for u in _env_csrf if u not in CSRF_TRUSTED_ORIGINS])

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# =======================
# Aplicaciones instaladas
# =======================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "products",
    "catalog",
]
SITE_ID = 1

# =======================
# Middleware
# =======================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# =======================
# Configuración de URLs
# =======================
ROOT_URLCONF = "photopro_app.urls"

# =======================
# Configuración de Plantillas
# =======================
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

# =======================
# Configuración de Autenticación
# =======================
WSGI_APPLICATION = "photopro_app.wsgi.application"

AUTH_USER_MODEL = "auth.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_VERIFICATION = "none"

# =======================
# Base de Datos
# =======================
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///db.sqlite3",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# =======================
# Validación de Contraseña
# =======================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =======================
# Internacionalización
# =======================
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# =======================
# Archivos Estáticos y Media
# =======================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = "/opt/render/project/src/media"   # Disco persistente de Render (5 GB)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =======================
# Auto IDs
# =======================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =======================
# Seguridad extra en producción
# =======================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Logging ---
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
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
