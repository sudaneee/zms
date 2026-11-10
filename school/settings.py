"""
Django settings for school project.

Deployment-specific values come from environment variables (the server's
.env file, see DEPLOYMENT.md). Defaults are for local development.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default):
    value = os.environ.get(name)
    return [item.strip() for item in value.split(',') if item.strip()] if value else default


# SECURITY WARNING: production must set DJANGO_SECRET_KEY. The fallback is
# only for local development and tests (`check --deploy` flags it).
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-local-development-only')

DEBUG = env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', [])

# Name printed on the sign-in page, menus, analysis sheets and verification page.
SCHOOL_NAME = os.environ.get('DJANGO_SCHOOL_NAME', 'Zaria Merit School')
# The section whose report cards are signed by the Form Master and Principal
# (the others: Class Teacher and Headteacher).
SENIOR_SECTION = 'Secondary'
# Print "No. in Class", "Class Position" and "Class Highest Average" on report
# cards. ZMS report cards have not shown them.
REPORT_SHOW_CLASS_POSITION = env_bool('DJANGO_REPORT_SHOW_CLASS_POSITION', False)
# Address printed in report-card QR codes (e.g. https://results.example.com);
# empty uses the address the cards were opened from.
PUBLIC_BASE_URL = os.environ.get('DJANGO_PUBLIC_URL', '')
# Raise to invalidate every result link already printed.
RESULT_LINK_VERSION = int(os.environ.get('DJANGO_RESULT_LINK_VERSION', 1))

# Production is served over HTTPS (nginx redirects plain HTTP), so cookies must
# never travel over plain HTTP.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', 0))


# Application definition

INSTALLED_APPS = [
    'src.apps.SrcConfig',
    'eval.apps.EvalConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'src.audit.AuditMiddleware',
    'src.accounts.ForcePasswordChangeMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'src.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'school.wsgi.application'


# Database
# DJANGO_DB_PATH lets development and rehearsal runs point at a copy of the
# live database instead of the real file.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

# Existing tables use 32-bit integer ids; keep them so upgrading Django does
# not generate migrations that rebuild every table.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

BACKUP_DIR = Path(os.environ.get('DJANGO_BACKUP_DIR', BASE_DIR / 'backups'))
BACKUP_KEEP = int(os.environ.get('DJANGO_BACKUP_KEEP', 30))


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static and media files

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', BASE_DIR / 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', BASE_DIR / 'media')


# Email (password reset links). Leave DJANGO_EMAIL_HOST unset to disable
# emailed resets; administrators can still reset passwords on the Users page.
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD', '')
EMAIL_USE_TLS = env_bool('DJANGO_EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@localhost')
PASSWORD_RESET_TIMEOUT = 2 * 60 * 60

# Uploaded spreadsheets larger than this are refused with a message.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Logging: errors go to the console (PythonAnywhere's error log) instead of
# being lost when DEBUG is off.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    # Refused (403) and missing (404) pages are expected; only log real errors.
    'loggers': {'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False}},
}
