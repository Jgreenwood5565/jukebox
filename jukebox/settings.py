"""Django settings for the jukebox.

Site specific configuration lives in ``settings_local.py`` inside the jukebox
storage directory (``~/.jukebox`` unless ``JUKEBOX_HOME`` is set). It is
written by ``jukebox jukebox_setup`` and executed at the end of this module,
so it may override or extend anything defined here.
"""

import os
import pkgutil
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


JUKEBOX_STORAGE_PATH = Path(os.environ.get("JUKEBOX_HOME", Path.home() / ".jukebox"))
try:
    JUKEBOX_STORAGE_PATH.mkdir(mode=0o750, parents=True, exist_ok=True)
except OSError:
    JUKEBOX_STORAGE_PATH = BASE_DIR

DEBUG = _env_bool("JUKEBOX_DEBUG")
SECRET_KEY = os.environ.get("JUKEBOX_SECRET_KEY", "")
ALLOWED_HOSTS = _env_list("JUKEBOX_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = _env_list("JUKEBOX_CSRF_TRUSTED_ORIGINS", "")

ADMINS = []
MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": JUKEBOX_STORAGE_PATH / "db.sqlite",
        "OPTIONS": {
            # a transaction that reads before writing (e.g. picking the next song)
            # fails with "database is locked" while another request writes, unless
            # it takes the write lock right away and waits for it
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

TIME_ZONE = os.environ.get("JUKEBOX_TIME_ZONE", "Europe/Berlin")
USE_TZ = True
LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("de", "Deutsch"),
    ("en", "English"),
]
USE_I18N = True

STATIC_URL = "/static/"
# static files are served straight from the apps, set STATIC_ROOT in
# settings_local.py only if you want to collectstatic for a separate web server
STATIC_ROOT = None
WHITENOISE_USE_FINDERS = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "jukebox.jukebox_web.middleware.content_security_policy",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "jukebox.urls"
WSGI_APPLICATION = "jukebox.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "jukebox.jukebox_web.context_processors.theme",
            ],
        },
    },
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "rest_framework",
    "social_django",
    "jukebox.jukebox_core",
    "jukebox.jukebox_web",
]

# automatically add installed jukebox plugins (jukebox_shout, jukebox_mpg123, ...)
_CORE_APPS = {"jukebox_core", "jukebox_web"}
JUKEBOX_PLUGINS = sorted(
    {
        module.name
        for module in pkgutil.iter_modules()
        if module.name.startswith("jukebox_") and module.name not in _CORE_APPS
    }
)
INSTALLED_APPS += JUKEBOX_PLUGINS

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "jukebox.jukebox_core.authentication.ThrottledBasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]
# social auth backend names offered on the login page, e.g. ["github", "twitter"]
SOCIAL_AUTH_ENABLED_BACKENDS = []
SOCIAL_AUTH_URL_NAMESPACE = "social"

LOGIN_URL = "/login"
LOGIN_ERROR_URL = "/login/error"
LOGIN_REDIRECT_URL = "/"
SOCIAL_AUTH_LOGIN_ERROR_URL = LOGIN_ERROR_URL
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL

# seconds of inactivity after which a user no longer counts as online for autoplay
SESSION_TTL = 300
# stay logged in for 30 days
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60

# allow logging in with a jukebox username and password (create users with
# "jukebox jukebox_adduser" or in the admin), in addition to social auth
JUKEBOX_LOCAL_LOGIN = _env_bool("JUKEBOX_LOCAL_LOGIN", True)
# failed logins per user and IP address before further attempts are refused,
# counts the login page, the admin and HTTP basic auth of the API
JUKEBOX_LOGIN_ATTEMPTS = 10
JUKEBOX_LOGIN_LOCKOUT = 15 * 60

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# addresses of reverse proxies (e.g. Caddy) whose X-Forwarded-For header tells
# the real client address, comma separated
JUKEBOX_TRUSTED_PROXIES = _env_list("JUKEBOX_TRUSTED_PROXIES", "")

# served through HTTPS (usually by a reverse proxy): only send cookies over HTTPS
# and send plain HTTP requests, e.g. to the server's own address, to the HTTPS
# site, the first of JUKEBOX_CSRF_TRUSTED_ORIGINS. Without that a login over
# plain HTTP loses its cookie and silently ends up at the login page again.
if _env_bool("JUKEBOX_HTTPS"):
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = LANGUAGE_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_SSL_HOST = urlparse(CSRF_TRUSTED_ORIGINS[0]).netloc if CSRF_TRUSTED_ORIGINS else None
    # the container's health check talks plain HTTP to itself
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]

# play the queue in the browser: the server keeps the "now playing" clock and
# every listener hears the same song. Turn off if a player plugin (jukebox_mpg123,
# jukebox_shout, ...) plays the queue instead, both would pick songs.
JUKEBOX_WEB_PLAYER = _env_bool("JUKEBOX_WEB_PLAYER", True)
# stream everything but MP3 as MP3 of this bitrate (needs ffmpeg), FLAC and
# hi-res files are far too big to stream as they are
JUKEBOX_TRANSCODE = _env_bool("JUKEBOX_TRANSCODE", True)
JUKEBOX_TRANSCODE_BITRATE = int(os.environ.get("JUKEBOX_TRANSCODE_BITRATE", "192"))

# "dark" or "light", every user can switch in the account menu
JUKEBOX_DEFAULT_THEME = os.environ.get("JUKEBOX_DEFAULT_THEME", "dark")

_local_settings = JUKEBOX_STORAGE_PATH / "settings_local.py"
if _local_settings.is_file():
    exec(compile(_local_settings.read_text(encoding="utf-8"), str(_local_settings), "exec"))

# settings files written by jukebox < 0.5 use django-social-auth names
_LEGACY_BACKENDS = {
    "social_auth.backends.facebook.FacebookBackend": "social_core.backends.facebook.FacebookOAuth2",
    "social_auth.backends.twitter.TwitterBackend": "social_core.backends.twitter.TwitterOAuth",
    "social_auth.backends.contrib.github.GithubBackend": "social_core.backends.github.GithubOAuth2",
}
_LEGACY_KEYS = {
    "FACEBOOK_APP_ID": "SOCIAL_AUTH_FACEBOOK_KEY",
    "FACEBOOK_API_SECRET": "SOCIAL_AUTH_FACEBOOK_SECRET",
    "TWITTER_CONSUMER_KEY": "SOCIAL_AUTH_TWITTER_KEY",
    "TWITTER_CONSUMER_SECRET": "SOCIAL_AUTH_TWITTER_SECRET",
    "GITHUB_APP_ID": "SOCIAL_AUTH_GITHUB_KEY",
    "GITHUB_API_SECRET": "SOCIAL_AUTH_GITHUB_SECRET",
}
AUTHENTICATION_BACKENDS = [_LEGACY_BACKENDS.get(b, b) for b in AUTHENTICATION_BACKENDS]
for _old, _new in _LEGACY_KEYS.items():
    if _old in globals() and _new not in globals():
        globals()[_new] = globals()[_old]
SOCIAL_AUTH_ENABLED_BACKENDS = list(SOCIAL_AUTH_ENABLED_BACKENDS)

if not SECRET_KEY or SECRET_KEY == "yourSecretKey":
    from jukebox.secret import load_or_create_secret_key

    SECRET_KEY = load_or_create_secret_key(JUKEBOX_STORAGE_PATH / "secret_key")
