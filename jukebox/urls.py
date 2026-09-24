from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path

# the admin's own login form has no failed login limit, use the jukebox login
admin.site.login = login_required(admin.site.login)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("jukebox.jukebox_web.urls")),
    path("", include("jukebox.jukebox_core.urls")),
    path("", include("social_django.urls", namespace="social")),
]
