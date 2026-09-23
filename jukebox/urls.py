from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("jukebox.jukebox_web.urls")),
    path("", include("jukebox.jukebox_core.urls")),
    path("", include("social_django.urls", namespace="social")),
]
