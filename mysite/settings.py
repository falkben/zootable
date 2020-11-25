"""
Django settings for mysite project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

import django_heroku
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
# STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# .env contains these:

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = ''
# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = 1
# ALLOWED_HOSTS = ""
# TIME_ZONE = "America/New_York"
# SECURE_SSL_REDIRECT = 0
# SESSION_COOKIE_SECURE = 0
# CSRF_COOKIE_SECURE = 0
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SECRET_KEY = os.getenv("SECRET_KEY")  # returns None if no env var
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(os.getenv("DEBUG", False)))
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1 .herokuapp.com").split()
TIME_ZONE = os.getenv("TIME_ZONE", "America/New_York")

# security options suggested from `python manage.py check --deploy`
# set to 1 to enable
SECURE_SSL_REDIRECT = bool(int(os.getenv("SECURE_SSL_REDIRECT", 1)))
SESSION_COOKIE_SECURE = bool(int(os.getenv("SESSION_COOKIE_SECURE", 1)))
CSRF_COOKIE_SECURE = bool(int(os.getenv("CSRF_COOKIE_SECURE", 1)))
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# for prod
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
# only matter w/ smtp backend
EMAIL_HOST = "smtp.zoho.com"
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "default")
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = "app@zootable.com"
DEFAULT_FROM_EMAIL = "app@zootable.com"  # used for all other email
SERVER_EMAIL = "app@zootable.com"  # used for email to ADMINS and MANAGERS

# add HSTS (HTTP Strict Transport Security)
# default to 0 seconds
# https://docs.djangoproject.com/en/3.1/ref/middleware/#http-strict-transport-security
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 0))

# photo storage path
# note: this is a custom setting
S3_MEDIA = bool(int(os.getenv("S3_MEDIA", 0)))
if S3_MEDIA:
    MEDIA_STORAGE = "zoo_checks.custom_storage.MediaStorageS3"
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = "us-east-1"
else:
    MEDIA_STORAGE = "zoo_checks.custom_storage.OverwriteStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# Application definition

INSTALLED_APPS = [
    "zoo_checks.apps.ZooChecksConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # "allauth.socialaccount.providers.google",
    # "allauth.socialaccount.providers.github",
    # "allauth.socialaccount.providers.facebook",
    # "allauth.socialaccount.providers.microsoft",
    "debug_toolbar",
]

if S3_MEDIA:
    INSTALLED_APPS += ["storages"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Simplified static file serving.
    # https://warehouse.python.org/project/whitenoise/
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "mysite.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "zootable",
        "USER": "zootable",
        "PASSWORD": "",
        "HOST": "",
    }
}

# for github actions
if os.getenv("GITHUB_WORKFLOW"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "postgres",
            "USER": "postgres",
            "PASSWORD": "postgres",
            "HOST": "127.0.0.1",
            "PORT": "5432",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # we were triggering this at default 1000

SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_SIGNUP_FORM_CLASS = "zoo_checks.forms.SignupForm"

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
if ADMIN_EMAIL is not None:
    ADMINS = [("admin", ADMIN_EMAIL)]

# Configure Django App for Heroku.
django_heroku.settings(locals())

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(asctime)s [%(process)d] [%(levelname)s] "
                + "pathname=%(pathname)s lineno=%(lineno)s "
                + "funcname=%(funcName)s %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {"zootable": {"handlers": ["console"], "level": "INFO"}},
}

# django debug toolbar allowlist
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#configuring-internal-ips
INTERNAL_IPS = ["127.0.0.1", "localhost"]
