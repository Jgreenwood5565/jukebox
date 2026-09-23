from django import forms


class IdForm(forms.Form):
    id = forms.IntegerField(min_value=1)


class ListForm(forms.Form):
    count = forms.IntegerField(required=False)
    page = forms.IntegerField(required=False)
    order_by = forms.CharField(max_length=10, required=False)
    order_direction = forms.CharField(
        max_length=4,
        help_text="'asc', 'desc'",
        required=False,
    )


class SongsForm(ListForm):
    search_term = forms.CharField(required=False)
    search_title = forms.CharField(required=False)
    search_artist = forms.CharField(required=False)
    search_album = forms.CharField(required=False)

    filter_year = forms.IntegerField(required=False)
    filter_genre = forms.IntegerField(required=False)
    filter_album_id = forms.IntegerField(required=False)
    filter_artist_id = forms.IntegerField(required=False)


# names used by jukebox < 0.5
ArtistsForm = AlbumsForm = GenresForm = YearsForm = ListForm
HistoryForm = FavouritesForm = QueueForm = ListForm
