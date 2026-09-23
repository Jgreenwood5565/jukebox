from django.contrib import admin

from .models import Album, Artist, Favourite, Genre, History, Player, Queue, Song


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ["Name"]
    search_fields = ["Name"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["Name"]
    search_fields = ["Name"]


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ["Title"]
    search_fields = ["Title"]


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ["Title", "Artist", "Album", "Year", "Genre"]
    list_select_related = ["Artist", "Album", "Genre"]
    search_fields = ["Title", "Artist__Name", "Album__Title", "Filename"]
    raw_id_fields = ["Artist", "Album", "Genre"]


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ["Song", "Created"]
    list_select_related = ["Song__Artist"]
    raw_id_fields = ["Song"]


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ["Song", "Created"]
    list_select_related = ["Song__Artist"]
    raw_id_fields = ["Song"]


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ["Song", "User", "Created"]
    list_select_related = ["Song__Artist", "User"]
    search_fields = ["User__username"]
    raw_id_fields = ["Song", "User"]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["Pid"]
