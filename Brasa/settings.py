from pathlib import Path
import os
from dotenv import load_dotenv

# ==============================================================================
# BASE / ENV
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent  # <-- corrigido (file_)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==============================================================================
# SEGURANÇA / DEPLOY
# ==============================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-test-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "0") == "1"

# Permite sobrescrever por env; inclui testserver p/ pytest-django
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,testserver,projetobrasa.azurewebsites.net"
).split(",")

# CSRF precisa de ORIGINS com esquema
def _csrf_from_hosts(hosts):
    out = set()
    for h in hosts:
        h = h.strip()
        if not h:
            continue
        if h.startswith("http://") or h.startswith("https://"):
            out.add(h)
        else:
            out.add(f"https://{h}")
    return sorted(out)

CSRF_TRUSTED_ORIGINS = _csrf_from_hosts(ALLOWED_HOSTS)

# Quando atrás de proxy/reverso (Azure), respeitar X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Travar segurança em produção
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==============================================================================
# APPS
# ==============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Ajuda o runserver a não conflitar com staticfiles (dev)
    "whitenoise.runserver_nostatic",

    "noticias",
    # "caca_links",  # adicione se o app estiver no projeto BRASA
]

# ==============================================================================
# MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # WhiteNoise logo após Security
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==============================================================================
# URLS / WSGI
# ==============================================================================
ROOT_URLCONF = "Brasa.urls"
WSGI_APPLICATION = "Brasa.wsgi.application"

# ==============================================================================
# TEMPLATES
# ==============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # use BASE_DIR / "templates" se tiver pasta global
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

# ==============================================================================
# BANCO DE DADOS
# ==============================================================================
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
    }
}

# ==============================================================================
# AUTENTICAÇÃO
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_REDIRECT_URL = "noticias:index"
LOGOUT_REDIRECT_URL = "noticias:index"

# ==============================================================================
# I18N / L10N / TZ
# ==============================================================================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC / MEDIA (WhiteNoise)
# ==============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Se tiver assets no app noticias/static, mantenha
STATICFILES_DIRS = [
    BASE_DIR / "noticias" / "static",
]

# WhiteNoise: arquivos comprimidos + manifest para cache busting
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cache local (ok para instância única)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-portal-noticias",
    }
}

# ==============================================================================
# DEFAULTS
# ==============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Garante existência do STATIC_ROOT no container (Azure)
os.makedirs(STATIC_ROOT, exist_ok=True)