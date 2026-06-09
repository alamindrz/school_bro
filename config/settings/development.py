import os
os.environ.setdefault('SECRET_KEY', 'django-insecure-dev-only-key-do-not-use-in-production')

from .base import *

# ------------------------------------------------------------------------------
# DEBUG
# ------------------------------------------------------------------------------
DEBUG = True

# ------------------------------------------------------------------------------
# ALLOWED HOSTS
# ------------------------------------------------------------------------------
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# ------------------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------------------

# Override base if needed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ------------------------------------------------------------------------------
# EMAIL (console backend for development)
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ------------------------------------------------------------------------------
# CACHING (simple local memory cache)
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ------------------------------------------------------------------------------
# CELERY (if you're using it)
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True  # tasks run synchronously in dev
CELERY_TASK_EAGER_PROPAGATES = True