"""
Django settings for pramana_core project.
"""

import os
from pathlib import Path
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from absolute path to .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    ENV_FILE = BASE_DIR / '.env'
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
except ImportError:
    pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-pramana-hackathon-development-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

# Host and Domain configuration
allowed_env = os.getenv('ALLOWED_HOSTS', '').strip()
if allowed_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['*']

# Gemini Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip()
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001').strip()

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'pramana',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# HTTPS / CSRF Trusted Origins for Vercel and local development
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
extra_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', '').strip()
if extra_csrf:
    for origin in extra_csrf.split(','):
        if origin.strip() and origin.strip() not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin.strip())

# Signed cookies for sessions (serverless friendly)
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

ROOT_URLCONF = 'pramana_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'pramana' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pramana_core.wsgi.application'

# Serverless Vercel environment detection
IS_VERCEL = bool(os.getenv('VERCEL') or os.getenv('NOW_REGION'))

# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
if IS_VERCEL:
    tmp_db = Path('/tmp') / 'db.sqlite3'
    bundled_db = BASE_DIR / 'db.sqlite3'
    if bundled_db.exists() and not tmp_db.exists():
        import shutil
        try:
            shutil.copy2(bundled_db, tmp_db)
        except Exception:
            pass
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': tmp_db,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT.mkdir(parents=True, exist_ok=True)



STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Fallback to AppDirectoriesFinder if a static file is not in STATIC_ROOT
WHITENOISE_USE_FINDERS = True


# Media files
MEDIA_URL = '/media/'

# Application data directories & FAISS storage
if IS_VERCEL:
    # On Vercel, the source directory is read-only. Writable operations target /tmp.
    DATA_DIR = Path('/tmp/data')
    UPLOADS_DIR = DATA_DIR / 'uploads'
    VECTOR_STORE_DIR = DATA_DIR / 'vector_store'
    MEDIA_ROOT = Path('/tmp/media')

    for folder in [DATA_DIR, UPLOADS_DIR, VECTOR_STORE_DIR, MEDIA_ROOT]:
        folder.mkdir(parents=True, exist_ok=True)

    # Seed pre-built vector index from repository bundle into /tmp if not already seeded
    bundled_vector_dir = BASE_DIR / 'data' / 'vector_store'
    if bundled_vector_dir.exists():
        import shutil
        for item in bundled_vector_dir.glob('*'):
            dest_file = VECTOR_STORE_DIR / item.name
            if not dest_file.exists():
                try:
                    shutil.copy2(item, dest_file)
                except Exception:
                    pass

    bundled_uploads_dir = BASE_DIR / 'data' / 'uploads'
    if bundled_uploads_dir.exists():
        import shutil
        for item in bundled_uploads_dir.glob('*'):
            dest_file = UPLOADS_DIR / item.name
            if not dest_file.exists():
                try:
                    shutil.copy2(item, dest_file)
                except Exception:
                    pass
else:
    DATA_DIR = BASE_DIR / 'data'
    UPLOADS_DIR = DATA_DIR / 'uploads'
    VECTOR_STORE_DIR = DATA_DIR / 'vector_store'
    MEDIA_ROOT = BASE_DIR / 'media'

    for folder in [DATA_DIR, UPLOADS_DIR, VECTOR_STORE_DIR, MEDIA_ROOT]:
        folder.mkdir(parents=True, exist_ok=True)

# Upload size limits (15 MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
