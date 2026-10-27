import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

IS_VERCEL = os.environ.get("VERCEL") == "1"
DEBUG = not IS_VERCEL and os.environ.get("DJANGO_DEBUG", "true").lower() in {
    "true", "1"
}
FLW_SECRET_KEY = os.environ.get("FLW_SECRET_KEY", "")
FLW_WEBHOOK_SECRET_HASH = os.environ.get("FLW_WEBHOOK_SECRET_HASH", "")
FLW_DATA_ENCRYPTION_KEY = os.environ.get("FLW_DATA_ENCRYPTION_KEY", "")
FLW_TRANSFERS_ENABLED = os.environ.get("FLW_TRANSFERS_ENABLED", "false").lower() in {
    "true",
    "1",
}
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-development-only",
)
if not DEBUG and SECRET_KEY == "django-insecure-local-development-only":
    raise ImproperlyConfigured("Définissez DJANGO_SECRET_KEY avant le déploiement.")

default_hosts = "localhost,127.0.0.1,.vercel.app" if IS_VERCEL else "localhost,127.0.0.1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", default_hosts).split(",")
    if host.strip()
]
vercel_url = os.environ.get("VERCEL_URL", "")
if vercel_url and vercel_url not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(vercel_url)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if IS_VERCEL:
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")
    if vercel_url:
        CSRF_TRUSTED_ORIGINS.append(f"https://{vercel_url}")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "reviews",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bongo_site.urls"

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

WSGI_APPLICATION = "bongo_site.wsgi.application"


database_url = os.environ.get("DATABASE_URL")
if IS_VERCEL and not database_url:
    raise ImproperlyConfigured(
        "DATABASE_URL doit pointer vers une base PostgreSQL persistante pour Vercel."
    )

if database_url:
    parsed_database_url = urlparse(database_url)
    if parsed_database_url.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL doit utiliser PostgreSQL.")
    if not parsed_database_url.hostname or not parsed_database_url.path.strip("/"):
        raise ImproperlyConfigured(
            "DATABASE_URL doit inclure un hôte et un nom de base PostgreSQL."
        )
    try:
        database_port = str(parsed_database_url.port or "")
    except ValueError as exc:
        raise ImproperlyConfigured("Le port de DATABASE_URL est invalide.") from exc
    database_options = {
        key: values[-1]
        for key, values in parse_qs(parsed_database_url.query).items()
    }
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_database_url.path.lstrip("/")),
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname or "",
            "PORT": database_port,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "sslmode": database_options.get(
                    "sslmode",
                    "require" if IS_VERCEL else "prefer",
                )
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Brazzaville"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
