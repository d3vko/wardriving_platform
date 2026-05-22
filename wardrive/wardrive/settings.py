import environ
import os
import datetime
from pathlib import Path
from celery.schedules import crontab
from kombu import Queue, Exchange

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)


INSTALLED_APPS = [
    "apps.users",  # debe ir antes de django.contrib.auth para el swap
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Config whitenoise
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "corsheaders",
    "drf_yasg",
    "django_filters",
    "django_celery_beat",
    "django_db_views",
    "channels",
    # Local apps
    "apps.wardriving",
    "apps.files",
    "apps.vendors",
    "apps.misc",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CORS configured to allow multiple origins
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Allow Locations and language support
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "wardrive.urls"

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

WSGI_APPLICATION = "wardrive.wsgi.application"

ASGI_APPLICATION = "wardrive.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env("DB_NAME", default=""),
        "USER": env("DB_USER", default=""),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default=""),
        "PORT": env("DB_PORT", default=0, cast=int),
    }
}


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


LANGUAGE_CODE = "es-mx"

TIME_ZONE = "America/Mexico_City"

USE_I18N = True

USE_TZ = True

FORCE_SCRIPT_NAME = env("FORCE_SCRIPT_NAME", default="").rstrip("/")
_script = f"{FORCE_SCRIPT_NAME}/" if FORCE_SCRIPT_NAME else ""

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# Ruta custom para no chocar con MinIO Console (que usa /static/ y /styles/)
STATIC_URL = env("STATIC_URL", default=f"{_script}static-wardrive/")

# Media: from env or default; when using S3, MEDIA_URL is typically /media/ (served by nginx proxy to MinIO)
MEDIA_URL = env("MEDIA_URL", default=f"{_script}media/")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# REST Config
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # https://www.django-rest-framework.org/api-guide/exceptions/#custom-exception-handling
    # "EXCEPTION_HANDLER": "rest.exception_handler.custom_exception_handler",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "api.exception_handler.custom_exception_handler",
}

# JWT headers
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=1),
}

# CORS
CORS_ALLOW_ALL_ORIGINS = env("CORS_ORIGIN_ALLOW_ALL", default=False, cast=bool)


# Storage: S3/MinIO when USE_S3=true, else filesystem
# Two buckets: one for wardrive (media), one for CTFd (ctfd)
# Bucket names must be S3-valid: lowercase, numbers, hyphens only (no underscores)
def _s3_bucket_name(name):
    if not name:
        return name
    return str(name).lower().replace("_", "-").strip() or "media"


USE_S3_STORAGE = env("USE_S3_STORAGE", default=False, cast=bool)
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = _s3_bucket_name(
    env("AWS_STORAGE_BUCKET_NAME", default="media")
)
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_FILE_OVERWRITE = env("AWS_S3_FILE_OVERWRITE", default=False, cast=bool)
AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="public-read")
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": env("AWS_S3_CACHE_CONTROL", default="max-age=86400"),
}

if (
    USE_S3_STORAGE
    and AWS_S3_ENDPOINT_URL
    and AWS_ACCESS_KEY_ID
    and AWS_SECRET_ACCESS_KEY
):
    _s3_options = {
        "endpoint_url": AWS_S3_ENDPOINT_URL,
        "access_key": AWS_ACCESS_KEY_ID,
        "secret_key": AWS_SECRET_ACCESS_KEY,
        "bucket_name": AWS_STORAGE_BUCKET_NAME,
        "region_name": AWS_S3_REGION_NAME,
        "file_overwrite": AWS_S3_FILE_OVERWRITE,
        "default_acl": AWS_DEFAULT_ACL,
        "object_parameters": AWS_S3_OBJECT_PARAMETERS,
        "querystring_auth": env("AWS_S3_QUERYSTRING_AUTH", default=False, cast=bool),
    }
    # Static y media en MinIO (bucket wardrive-storage; static bajo prefijo "static/")
    # MinIOStaticStorage genera URLs con STATIC_URL para que el navegador pida a nginx, no a minio:9000
    STORAGES = {
        "staticfiles": {
            "BACKEND": "wardrive.storage_backends.MinIOStaticStorage",
            "OPTIONS": {
                **_s3_options,
                "location": "static",
            },
        },
        "default": {
            "BACKEND": "wardrive.storage_backends.MinIOS3Storage",
            "OPTIONS": _s3_options,
        },
    }
else:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
    }
# ----- Email / SMTP -----
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# ----- Email branding (used in HTML templates) -----
EMAIL_SITE_NAME = env("EMAIL_SITE_NAME", default="Wardrive")
EMAIL_SUPPORT_EMAIL = env("EMAIL_SUPPORT_EMAIL", default="")
# Absolute URL of the logo image shown in email header
EMAIL_LOGO_URL = env("EMAIL_LOGO_URL", default="")


def _env_multiline(key: str, default: str) -> str:
    """Read an env var and convert literal \\n sequences to real newlines (mirrors Vite's parseEnvMultiline)."""
    return env(key, default=default).replace("\\n", "\n")


# Welcome email — configurable copy (use \n in .env to produce line breaks / list items)
EMAIL_WELCOME_INTRO = _env_multiline(
    "EMAIL_WELCOME_INTRO",
    (
        "Bienvenido a la plataforma del CTF de wardriving.\n"
        "Tu cuenta está lista: aquí podrás participar subiendo capturas y consultando los resultados del evento."
    ),
)
EMAIL_WELCOME_FEATURES = _env_multiline(
    "EMAIL_WELCOME_FEATURES",
    (
        "Subir archivos de captura (Upload)\n"
        "Explorar mapas de wardriving WiFi y LTE\n"
        "Revisar analytics del evento\n"
        "Descargar exportaciones KML"
    ),
)

# ----- Password reset via API (SPA) -----
# Full base URL including basename, e.g. https://host/ctf
# Falls back to the first CSRF_TRUSTED_ORIGINS entry + FORCE_SCRIPT_NAME (dev only).
_reset_base_fallback = ""
PASSWORD_RESET_FRONTEND_BASE_URL = env("PASSWORD_RESET_FRONTEND_BASE_URL", default=_reset_base_fallback)
PASSWORD_RESET_PATH = env("PASSWORD_RESET_PATH", default="reset-password")

# URL used in welcome email "go to app" button
FRONTEND_LOGIN_URL = env("FRONTEND_LOGIN_URL", default="")

# Related to documentation
SWAGGER_EMAIL = env("SWAGGER_EMAIL", default="example@mail.com")
SWAGGER_AUTHOR = env("SWAGGER_AUTHOR", default="not specified")
SWAGGER_CONTACT_URL = env(
    "SWAGGER_CONTACT_URL",
    default="https://static.wikia.nocookie.net/memeaventuras/images/5/51/Ola.jpg/revision/latest?cb=20140613225246&path-prefix=es",
)
SWAGGER_LICENSE = env("SWAGGER_LICENSE", default="Not specified yet")


# Swagger Settings
SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": env(
        "SWAGGER_USE_SESSION_AUTH", default=False, cast=bool
    ),  # Disable session authentication
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        },
    },
}

# Redis Configuration
# Prefer full REDIS_URL from env (e.g. Railway: redis://default:PASSWORD@host:port/0)
REDIS_USERNAME = env("REDIS_USERNAME", default="default")
REDIS_URL = env("REDIS_URL", default="")
if not REDIS_URL.strip():
    REDIS_HOST = env("REDIS_HOST", default="localhost")
    REDIS_PORT = env("REDIS_PORT", default=6379, cast=int)
    REDIS_DB = env("REDIS_DB", default=0, cast=int)
    REDIS_PASSWORD = env("REDIS_PASSWORD", default="")
    if REDIS_HOST and REDIS_PORT:
        if REDIS_PASSWORD:
            REDIS_URL = (
                f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            )
        else:
            REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
# Redis 6+ ACL (e.g. Railway) requires a username; normalize redis://:password@host -> redis://USERNAME:password@host
if REDIS_URL.strip():
    from urllib.parse import urlparse, urlunparse, quote

    _parsed = urlparse(REDIS_URL)
    if _parsed.netloc.startswith(":"):
        _pwd = _parsed.netloc[1:].split("@")[0]
        _host = _parsed.netloc.split("@")[-1]
        _user = quote(REDIS_USERNAME, safe="")
        REDIS_URL = urlunparse(
            _parsed._replace(netloc=f"{_user}:{quote(_pwd, safe='')}@{_host}")
        )


def _redis_url_with_db(url: str, db: int, username: str = None) -> str:
    """Return the same Redis URL with the given database number (path)."""
    if not url or not url.strip():
        return ""
    from urllib.parse import urlparse, urlunparse, quote

    if username is None:
        username = REDIS_USERNAME
    parsed = urlparse(url)
    # path is like /0 or /1; replace with /db
    new_path = f"/{db}"
    # Redis 6+ ACL (e.g. Railway) requires username; redis://:password@host -> username:password@host
    netloc = parsed.netloc
    if netloc.startswith(":"):
        password = netloc[1:].split("@")[0]
        host_part = netloc.split("@")[-1]
        netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{host_part}"
    return urlunparse(parsed._replace(netloc=netloc, path=new_path))


# Celery: use REDIS_URL with db 0/1 when broker/result URLs are not set (e.g. Railway single REDIS_URL)
_default_broker = _redis_url_with_db(REDIS_URL, 0) or "redis://localhost:6379/0"
_default_result = _redis_url_with_db(REDIS_URL, 1) or "redis://localhost:6379/1"
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=_default_broker)
_result_backend_from_env = env("CELERY_RESULT_BACKEND", default=_default_result)
# If REDIS_URL has credentials but CELERY_RESULT_BACKEND is redis without auth (e.g. Railway),
# use REDIS_URL with same DB so Redis auth succeeds.
if (
    REDIS_URL.strip()
    and "@" in REDIS_URL
    and _result_backend_from_env.strip().lower().startswith("redis://")
    and "@" not in _result_backend_from_env
):
    from urllib.parse import urlparse

    parsed = urlparse(_result_backend_from_env)
    try:
        _result_db = int((parsed.path or "/1").strip("/") or "1")
    except ValueError:
        _result_db = 1
    CELERY_RESULT_BACKEND = _redis_url_with_db(REDIS_URL, _result_db)
else:
    CELERY_RESULT_BACKEND = _result_backend_from_env
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Mexico_City"
CELERY_ENABLE_UTC = False
# --- Sharding by (uploaded_by, device_source) ---
CELERY_SHARDS = int(os.getenv("CELERY_SHARDS", "2"))
CELERY_TASK_DEFAULT_QUEUE = "proc_0"
QUEUE_ARGS = {"x-max-priority": 10}

CELERY_TASK_QUEUES = tuple(
    Queue(
        name=f"proc_{i}",
        exchange=Exchange(f"proc_{i}"),
        routing_key=f"proc_{i}",
        **{"queue_arguments": QUEUE_ARGS},
    )
    for i in range(CELERY_SHARDS)
)


def _shard_for(uploaded_by_id, device_source, n=CELERY_SHARDS):
    key = f"{uploaded_by_id}:{device_source}"
    return f"proc_{(hash(key) % n)}"


def route_by_pair(name, args, kwargs, options, task=None, **_):
    if name.endswith("process_file"):
        ub = kwargs.get("_uploaded_by_id")
        ds = kwargs.get("_device_source")
        if ub is not None and ds is not None:
            q = _shard_for(ub, ds)
            # e.g. higher priority for critical sources (closer to 10)
            prio = 8 if ds in {"wardriving_app"} else 5
            return {"queue": q, "routing_key": q, "priority": prio}
    return None


CELERY_TASK_ROUTES = (route_by_pair,)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

APPEND_SLASH = False
USE_X_FORWARDED_HOST = True

# Django Channels (WebSocket). In-memory is enough for single-process; use Redis in multi-worker.
if REDIS_URL.strip():
    try:
        import channels_redis  # noqa: F401, F403

        _channel_hosts = [_redis_url_with_db(REDIS_URL, 3)]
        CHANNEL_LAYERS = {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {"hosts": _channel_hosts},
            },
        }
    except ImportError:
        CHANNEL_LAYERS = {
            "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
        }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://*.ngrok.io",
        "https://*.ngrok.io",
        "http://*.ngrok-free.app",
        "https://*.ngrok-free.app",
        "http://*.tcp.ngrok.io",
        "https://*.tcp.ngrok.io",
    ],
)
