from pathlib import Path
from datetime import timedelta
import os
import dj_database_url

# =====================================================
# BASE DIRECTORY
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'

if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# =====================================================
# SECURITY
# =====================================================
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-this-in-production'
)

DEBUG = os.environ.get(
    'DJANGO_DEBUG',
    'False'
).lower() == 'true'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    '*'
).split(',')

# =====================================================
# APPLICATIONS
# =====================================================
INSTALLED_APPS = [

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',

    # THIRD PARTY
    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'djoser',

    # LOCAL
    'core.apps.CoreConfig',
]

# =====================================================
# MIDDLEWARE
# =====================================================
MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =====================================================
# ROOT URL
# =====================================================
ROOT_URLCONF = 'enrollment_system.urls'

# =====================================================
# TEMPLATES
# =====================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# =====================================================
# WSGI
# =====================================================
WSGI_APPLICATION = 'enrollment_system.wsgi.application'
ASGI_APPLICATION = 'enrollment_system.asgi.application'

# =====================================================
# DATABASE
# =====================================================
IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

DATABASE_URL_ENV_KEYS = (
    "DATABASE_URL",
    "DATABASE_PRIVATE_URL",
    "DATABASE_PUBLIC_URL",
    "POSTGRES_URL",
    "POSTGRES_PRIVATE_URL",
    "POSTGRES_PUBLIC_URL",
)
DATABASE_SOURCE = next(
    (key for key in DATABASE_URL_ENV_KEYS if os.environ.get(key)),
    None,
)
DATABASE_URL = os.environ.get(DATABASE_SOURCE) if DATABASE_SOURCE else None

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=os.environ.get("POSTGRES_SSL_REQUIRE", "false").lower() == "true",
        )
    }
elif all(
    os.environ.get(key)
    for key in ("PGDATABASE", "PGUSER", "PGPASSWORD", "PGHOST")
):
import dj_database_url
import os

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL")
    )
}
    DATABASE_SOURCE = "PGDATABASE/PGUSER/PGPASSWORD/PGHOST"
elif all(
    os.environ.get(key)
    for key in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST")
):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
    DATABASE_SOURCE = "POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_HOST"
elif IS_RAILWAY:
    raise RuntimeError(
        "Railway database is not connected to this Django service. Add one "
        "of these variables to the Django/backend service: "
        "DATABASE_URL=${{ Postgres.DATABASE_URL }} or "
        "DATABASE_PRIVATE_URL=${{ Postgres.DATABASE_PRIVATE_URL }}. "
        "DATABASE_PUBLIC_URL and split PG* or POSTGRES_* variables are also supported."
    )
else:
    DATABASES = {
        "default": dj_database_url.parse(
            "postgres://postgres:123@localhost:5432/enrollment_db",
            conn_max_age=600,
        )
    }
    DATABASE_SOURCE = "local fallback"

# =====================================================
# AUTH
# =====================================================
AUTH_USER_MODEL = 'core.User'

# =====================================================
# PASSWORD VALIDATION
# =====================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =====================================================
# INTERNATIONALIZATION
# =====================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =====================================================
# STATIC FILES (RAILWAY FIX)
# =====================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =====================================================
# MEDIA FILES
# =====================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =====================================================
# DEFAULT PRIMARY KEY
# =====================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================
# CORS
# =====================================================
DEFAULT_CORS_ALLOWED_ORIGINS = [
    'http://localhost:8081',
    'http://127.0.0.1:8081',
    'http://localhost:19006',
    'http://127.0.0.1:19006',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

CORS_ALLOW_ALL_ORIGINS = os.environ.get(
    'CORS_ALLOW_ALL_ORIGINS',
    str(DEBUG)
).lower() == 'true'

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        ','.join(DEFAULT_CORS_ALLOWED_ORIGINS)
    ).split(',')
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        ','.join(DEFAULT_CORS_ALLOWED_ORIGINS)
    ).split(',')
    if origin.strip()
]

# =====================================================
# REST FRAMEWORK
# =====================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

# =====================================================
# SIMPLE JWT
# =====================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# =====================================================
# DJOSER
# =====================================================
DJOSER = {
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': True,
    'SEND_ACTIVATION_EMAIL': False,
}

# =====================================================
# EMAIL
# =====================================================
EMAIL_HOST_USER = (
    os.environ.get('EMAIL_HOST_USER')
    or os.environ.get('GMAIL_EMAIL')
    or ''
)
EMAIL_HOST_PASSWORD = (
    os.environ.get('EMAIL_HOST_PASSWORD')
    or os.environ.get('GMAIL_APP_PASSWORD')
    or ''
).replace(' ', '')
EMAIL_HAS_SMTP_CREDENTIALS = bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_HAS_SMTP_CREDENTIALS
    else 'django.core.mail.backends.console.EmailBackend'
)

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '20'))

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise RuntimeError('EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be true.')

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'Enrollment <{EMAIL_HOST_USER}>'
    if EMAIL_HOST_USER
    else 'Enrollment <noreply@student-enrollment.local>'
)

# =====================================================
# UPLOAD LIMITS
# =====================================================
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760
FILE_UPLOAD_PERMISSIONS = 0o644

# =====================================================
# OLLAMA CHATBOT
# =====================================================
OLLAMA_BASE_URL = os.environ.get(
    'OLLAMA_BASE_URL',
    'http://localhost:11434'
).rstrip('/')
OLLAMA_CHAT_MODEL = os.environ.get(
    'OLLAMA_CHAT_MODEL',
    'qwen2.5:0.5b'
)
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '30'))
