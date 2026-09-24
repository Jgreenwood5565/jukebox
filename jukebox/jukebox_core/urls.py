from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .feeds import QueueFeed

urlpatterns = [
    path("api/v1/songs", views.songs.as_view(), name="jukebox_api_songs"),
    path("api/v1/songs/skip", views.songs_skip.as_view(), name="jukebox_api_songs_skip"),
    path(
        "api/v1/songs/current",
        views.songs_current.as_view(),
        name="jukebox_api_songs_current",
    ),
    path(
        "api/v1/songs/<int:song_id>/stream",
        views.songs_stream.as_view(),
        name="jukebox_api_songs_stream",
    ),
    path(
        "api/v1/songs/<int:song_id>/cover",
        views.songs_cover.as_view(),
        name="jukebox_api_songs_cover",
    ),
    path("api/v1/artists", views.artists.as_view(), name="jukebox_api_artists"),
    path("api/v1/albums", views.albums.as_view(), name="jukebox_api_albums"),
    path("api/v1/genres", views.genres.as_view(), name="jukebox_api_genres"),
    path("api/v1/years", views.years.as_view(), name="jukebox_api_years"),
    path("api/v1/history", views.history.as_view(), name="jukebox_api_history"),
    path("api/v1/history/my", views.history_my.as_view(), name="jukebox_api_history_my"),
    path("api/v1/favourites", views.favourites.as_view(), name="jukebox_api_favourites"),
    path(
        "api/v1/favourites/<int:song_id>",
        views.favourites_item.as_view(),
        name="jukebox_api_favourites_item",
    ),
    path("api/v1/queue", views.queue.as_view(), name="jukebox_api_queue"),
    path(
        "api/v1/queue/<int:song_id>",
        views.queue_item.as_view(),
        name="jukebox_api_queue_item",
    ),
    path("api/v1/ping", views.ping.as_view(), name="jukebox_api_ping"),
    # the queue is only for people with an account
    path("feed/", login_required(QueueFeed()), name="jukebox_feed"),
]
