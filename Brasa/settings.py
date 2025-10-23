# =======================================
# BRASA — Django settings (produção Azure)
# =======================================

from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# ==============================================================================
# BASE
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent  # __file_ (corrigido)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==============================================================================
# SEGURANÇA
# ==============================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = False

ALLOWED_HOSTS = ["brasa.azurewebsites.net", "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["https://brasa.azurewebsites.net"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = True

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==============================================================================
# APPS
# ==============================================================================
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "storages",  
    "noticias",
]

# ==============================================================================
# MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Brasa.urls"

# ==============================================================================
# TEMPLATES
# ==============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = "Brasa.wsgi.application"

# ==============================================================================
# BANCO DE DADOS
# ==============================================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ==============================================================================
# SENHAS
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ==============================================================================
# I18N / TZ
# ==============================================================================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# ARQUIVOS ESTÁTICOS (CSS/JS) — WhiteNoise
# ==============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "noticias" / "static", 
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ==============================================================================
# MÍDIA (Uploads de Imagens) — Azure Blob em produção
# ==============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")        
AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY", "")
AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING", "")
AZURE_MEDIA_CONTAINER = os.getenv("AZURE_MEDIA_CONTAINER", "media") 

if AZURE_CONNECTION_STRING or (AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY):
    DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
    AZURE_CONTAINER = AZURE_MEDIA_CONTAINER
    AZURE_CUSTOM_DOMAIN = f"{AZURE_ACCOUNT_NAME}.blob.core.windows.net"
    MEDIA_URL = f"https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/"
    AZURE_OVERWRITE_FILES = False  
    # AZURE_URL_EXPIRATION_SECS = 3600  
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ==============================================================================
# AUTENTICAÇÃO (mantido do seu BRASA)
# ==============================================================================
LOGIN_REDIRECT_URL = "noticias:index"
LOGOUT_REDIRECT_URL = "noticias:index"