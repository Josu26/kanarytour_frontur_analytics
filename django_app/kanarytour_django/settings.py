"""
Django settings for kanarytour_django project.

Base: Django 6.0
"""

from pathlib import Path
import os

# BASE_DIR = carpeta raíz del proyecto (kanarytour_frontur_analytics)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =========================
#  SEGURIDAD / ENTORNO
# =========================

# En producción, Render leerá SECRET_KEY de las variables de entorno
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-+on=-v+jkaysl(xb56sm!&-5*62m)s^$5n_t)z0*k9o)o_gj_q",  # solo para desarrollo local
)

# En local puedes dejar DJANGO_DEBUG=True, en producción ponla a False
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# Ajusta estos valores cuando tengas hosting/domino
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".onrender.com",        # para cuando despliegues en Render
    "kanarios.es",        # <-- cámbialo por tu dominio real
    ".kanarios.es",       # <-- cámbialo por tu dominio real
]

CSRF_TRUSTED_ORIGINS = [
    "https://kanarios.es",         # <-- cámbialo por tu dominio real
    "https://www.kanarios.es",     # <-- cámbialo por tu dominio real
    "https://*.onrender.com",
]

# =========================
#  APLICACIONES
# =========================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Apps de terceros
    "rest_framework",
    "django.contrib.humanize",

    # Tu app
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Whitenoise para servir static en producción
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kanarytour_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "kanarytour_django.wsgi.application"

# =========================
#  BASE DE DATOS
# =========================

# De momento SQLite (suficiente para portfolio). Si luego quieres Postgres en Render, lo cambiamos.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =========================
#  PASSWORDS
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =========================
#  I18N
# =========================

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Atlantic/Canary"

USE_I18N = True
USE_TZ = True

# =========================
#  STATIC
# =========================

STATIC_URL = "/static/"

# Carpeta donde collectstatic volcará todo (para producción)
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise: servir estáticos comprimidos
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =========================
#  DEFAULTS
# =========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
