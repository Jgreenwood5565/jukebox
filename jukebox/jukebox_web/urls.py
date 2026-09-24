from django.urls import path
from django.views.i18n import JavaScriptCatalog

from . import users, views

urlpatterns = [
    path("", views.index, name="jukebox_web_index"),
    path("healthz", views.healthz, name="jukebox_web_healthz"),
    path("login", views.LoginView.as_view(), name="jukebox_web_login"),
    path("login/error", views.LoginErrorView.as_view(), name="jukebox_web_login_error"),
    path("language/set/<slug:language>", views.language, name="jukebox_web_language"),
    path("theme/set/<slug:theme>", views.theme, name="jukebox_web_theme"),
    path("logout", views.logout, name="jukebox_web_logout"),
    path("users", users.users, name="jukebox_web_users"),
    path("users/<int:user_id>", users.user_edit, name="jukebox_web_user_edit"),
    path("users/<int:user_id>/password", users.user_password, name="jukebox_web_user_password"),
    path("users/<int:user_id>/delete", users.user_delete, name="jukebox_web_user_delete"),
    path(
        "jsi18n/",
        JavaScriptCatalog.as_view(packages=["jukebox.jukebox_web"]),
        name="javascript-catalog",
    ),
]
