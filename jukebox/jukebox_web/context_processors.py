from django.conf import settings

THEMES = ("dark", "light")
THEME_COOKIE_NAME = "jukebox_theme"


def get_theme(request):
    theme = request.COOKIES.get(THEME_COOKIE_NAME)
    if theme in THEMES:
        return theme
    return settings.JUKEBOX_DEFAULT_THEME if settings.JUKEBOX_DEFAULT_THEME in THEMES else "dark"


def theme(request):
    return {"theme": get_theme(request)}
