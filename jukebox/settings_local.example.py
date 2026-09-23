# Example site configuration. Copy to ~/.jukebox/settings_local.py (or run
# ``jukebox jukebox_setup``) and adjust. Everything in jukebox/settings.py can
# be overridden here.

ADMINS = [("Admin", "admin@example.com")]

# Never enable DEBUG on a jukebox reachable by other people.
DEBUG = False

# Host names/IPs used to reach the jukebox in the browser.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "jukebox.example.com"]

# Leave unset to have a random key generated in ~/.jukebox/secret_key.
# SECRET_KEY = "..."

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "social_core.backends.github.GithubOAuth2",
]
SOCIAL_AUTH_ENABLED_BACKENDS = ["github"]

SOCIAL_AUTH_GITHUB_KEY = "your-github-client-id"
SOCIAL_AUTH_GITHUB_SECRET = "your-github-client-secret"
