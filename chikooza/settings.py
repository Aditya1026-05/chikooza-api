"""Django settings for the Chikooza API."""

import os
from pathlib import Path

import dj_database_url
import environ
from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
# Deployment environment variables take precedence over local `.env` values.
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = _env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false."
        )
    SECRET_KEY = "django-insecure-local-dev-only-change-before-deploy"

CORS_ALLOW_ALL_ORIGINS = _env_bool("CHIKOOZA_CORS_ALLOW_ALL", DEBUG)
CORS_ALLOWED_ORIGINS = _env_list("CHIKOOZA_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = default_headers + ("Access-Control-Allow-Origin",)
CORS_ALLOW_CREDENTIALS = True
APPEND_SLASH = False
USE_TZ = False
ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,.herokuapp.com",
)

# Application definition
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "rest_framework",
    "oauth2_provider",
    "corsheaders",
    "common",
    "farm",
    "flocks",
    "purchase",
    "dailydata",
    "sales",
    "chatbot",
    "aibot",
]

JAZZMIN_SETTINGS = {
    "site_title": "Chikooza Admin",
    "site_header": "Chikooza Admin",
    "site_brand": "Chikooza",
    "welcome_sign": "Manage farmers, flocks, daily data, purchases, and sales",
    "copyright": "Chikooza",
    "custom_css": "common/admin.css",
    "use_google_fonts_cdn": False,
    "search_model": [
        "common.Users",
        "farm.Farm",
        "flocks.Flock",
        "purchase.Purchase",
        "dailydata.DailyData",
        "sales.Sales",
    ],
    "topmenu_links": [
        {
            "name": "Workflow",
            "url": "admin:index",
            "permissions": ["common.view_users"],
        },
        {
            "name": "Farmers",
            "model": "common.Users",
        },
        {
            "name": "Flocks",
            "model": "flocks.Flock",
        },
        {
            "name": "Daily data",
            "model": "dailydata.DailyData",
        },
    ],
    "show_sidebar": True,
    "navigation_expanded": False,
    "hide_apps": ("oauth2_provider", "auth", "users"),
    "hide_models": (
        "common.Otp",
        "common.EmailOtp",
        "common.UsersForgotPassword",
        "chatbot.KnowledgeChunk",
        "chatbot.ChatMessage",
    ),
    "order_with_respect_to": [
        "common.Users",
        "common.RegistrationApprovalPolicy",
        "farm",
        "flocks",
        "dailydata",
        "purchase",
        "sales",
        "chatbot",
        "aibot",
    ],
    "icons": {
        "common": "fas fa-user-check",
        "common.Users": "fas fa-users",
        "common.RegistrationApprovalPolicy": "fas fa-clipboard-check",
        "farm": "fas fa-warehouse",
        "farm.Farm": "fas fa-tractor",
        "flocks": "fas fa-layer-group",
        "flocks.Flock": "fas fa-list",
        "dailydata": "fas fa-calendar-check",
        "dailydata.DailyData": "fas fa-clipboard-list",
        "dailydata.FlockVaccination": "fas fa-syringe",
        "purchase": "fas fa-shopping-cart",
        "purchase.Purchase": "fas fa-receipt",
        "sales": "fas fa-file-invoice-dollar",
        "sales.Sales": "fas fa-chart-line",
        "chatbot": "fas fa-comments",
        "aibot": "fas fa-robot",
    },
}
JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "accent": "accent-success",
    "navbar": "navbar-white navbar-light",
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_compact_style": True,
    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-secondary",
        "info": "btn-outline-primary",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
# Base URL used to build OAuth and account callback URLs.
HOSTNAME = os.environ.get("CHIKOOZA_API_BASE_URL", "http://127.0.0.1:8002/")
if not HOSTNAME.endswith("/"):
    HOSTNAME = f"{HOSTNAME}/"
CHIKOOZA_UI_BASE_URL = os.environ.get("CHIKOOZA_UI_BASE_URL", "http://localhost:5173")

# Optional fixed OTP for local MVP testing. Leave unset in production.
CHIKOOZA_FIXED_OTP = os.environ.get("CHIKOOZA_FIXED_OTP")

# Email delivery is opt-in locally and should use SMTP in production.
CHIKOOZA_EMAIL_OTP_DELIVERY_ENABLED = _env_bool(
    "CHIKOOZA_EMAIL_OTP_DELIVERY_ENABLED", False
)
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@chikooza.local")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.PageNotFoundMiddleware",
    "common.middleware.AuthenticationErrorMessage",
    "chatbot.middleware.LoggingMiddleware",
]
ROOT_URLCONF = "chikooza.urls"

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
            ]
        },
    }
]

WSGI_APPLICATION = "chikooza.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db1.sqlite3"),
    }
}

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=not DEBUG,
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
OAUTH2_PROVIDER = {
    "SCOPES": {
        "read": "Read scope",
        "create": "create scope",
        "update": "update scope",
        "delete": "delete scope",
        "groups": "Access to your groups",
    },
    "ACCESS_TOKEN_EXPIRE_SECONDS": 31556952,
    "ACCESS_TOKEN_GENERATOR": "common.token_generator.generate_token",
}

# Optional untracked developer overrides.
try:
    from .local_settings import *
except ImportError:
    pass
