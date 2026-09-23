import os

from django.core.management.utils import get_random_secret_key


def load_or_create_secret_key(path):
    """Return the secret key stored at ``path``, creating it on first use."""
    try:
        with open(path, encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    except FileNotFoundError:
        pass

    key = get_random_secret_key()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key)
    return key
