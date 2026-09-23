from django.urls import path
from django.views.i18n import JavaScriptCatalog

from . import views

urlpatterns = [
    path("", views.index, name="jukebox_web_index"),
    path("login", views.login, name="jukebox_web_login"),
    path("login/error", views.login_error, name="jukebox_web_login_error"),
    path("language/set/<slug:language>", views.language, name="jukebox_web_language"),
    path("logout", views.logout, name="jukebox_web_logout"),
    path(
        "jsi18n/",
        JavaScriptCatalog.as_view(packages=["jukebox.jukebox_web"]),
        name="javascript-catalog",
    ),
]
