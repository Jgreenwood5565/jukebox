from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import api, forms
from .models import Favourite, History, Queue, Song


class JukeboxAPIView(APIView):
    permission_classes = [IsAuthenticated]
    api_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # refresh the session expiry, active sessions decide what autoplay picks
        request.session.modified = True

    def get_api(self):
        api_obj = self.api_class()
        api_obj.set_user_id(self.request.user.id)
        return api_obj


class ListView(JukeboxAPIView):
    form_class = forms.ListForm
    item_url_name = None

    def apply_options(self, api_obj, data):
        if data.get("order_by"):
            if data.get("order_direction"):
                api_obj.set_order_by(data["order_by"], data["order_direction"])
            else:
                api_obj.set_order_by(data["order_by"])

        if data.get("count") is not None:
            api_obj.set_count(data["count"])

    def get(self, request):
        api_obj = self.get_api()

        # invalid values are ignored, the valid ones are still applied
        form = self.form_class(request.GET)
        form.is_valid()
        self.apply_options(api_obj, form.cleaned_data)

        page = form.cleaned_data.get("page")
        result = api_obj.index(1 if page is None else page)

        if self.item_url_name:
            for item in result["itemList"]:
                item["url"] = reverse(self.item_url_name, kwargs={"song_id": item["id"]})

        return Response(self.finalize(result, form))

    def finalize(self, result, form):
        return result


class songs(ListView):
    api_class = api.songs
    form_class = forms.SongsForm

    def apply_options(self, api_obj, data):
        super().apply_options(api_obj, data)

        if data.get("search_term"):
            api_obj.set_search_term(data["search_term"])
        if data.get("search_title"):
            api_obj.set_search_title(data["search_title"])
        if data.get("search_artist"):
            api_obj.set_search_artist_name(data["search_artist"])
        if data.get("search_album"):
            api_obj.set_search_album_title(data["search_album"])

        if data.get("filter_artist_id") is not None:
            api_obj.set_filter_artist_id(data["filter_artist_id"])
        if data.get("filter_album_id") is not None:
            api_obj.set_filter_album_id(data["filter_album_id"])
        if data.get("filter_genre") is not None:
            api_obj.set_filter_genre(data["filter_genre"])
        if data.get("filter_year") is not None:
            api_obj.set_filter_year(data["filter_year"])

    def finalize(self, result, form):
        result["form"] = form.cleaned_data
        return result


class songs_current(JukeboxAPIView):
    def get(self, request):
        try:
            current = api.history().getCurrent()
        except History.DoesNotExist:
            current = {}

        return Response(data=current)


class songs_skip(JukeboxAPIView):
    def post(self, request):
        api.songs().skipCurrentSong()
        return Response(status=status.HTTP_204_NO_CONTENT)


class artists(ListView):
    api_class = api.artists


class albums(ListView):
    api_class = api.albums


class genres(ListView):
    api_class = api.genres


class years(ListView):
    api_class = api.years


class history(ListView):
    api_class = api.history


class history_my(ListView):
    api_class = api.history_my


class queue(ListView):
    api_class = api.queue
    item_url_name = "jukebox_api_queue_item"

    def post(self, request):
        form = forms.IdForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        song_id = form.cleaned_data["id"]

        try:
            vote_count = self.get_api().add(song_id)
        except Song.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(
            status=status.HTTP_201_CREATED,
            data={"id": song_id, "count": vote_count},
            headers={"Location": reverse(self.item_url_name, kwargs={"song_id": song_id})},
        )


class queue_item(JukeboxAPIView):
    api_class = api.queue

    def get(self, request, song_id):
        try:
            item = self.get_api().get(song_id)
        except Queue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        item["url"] = reverse("jukebox_api_queue_item", kwargs={"song_id": item["id"]})
        return Response(data=item)

    def delete(self, request, song_id):
        try:
            return Response(data=self.get_api().remove(song_id))
        except Queue.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class favourites(ListView):
    api_class = api.favourites
    item_url_name = "jukebox_api_favourites_item"

    def post(self, request):
        form = forms.IdForm(request.data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        song_id = form.cleaned_data["id"]

        try:
            created = self.get_api().add(song_id)
        except Song.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            data={"id": song_id},
            headers={"Location": reverse(self.item_url_name, kwargs={"song_id": song_id})},
        )


class favourites_item(JukeboxAPIView):
    api_class = api.favourites

    def get(self, request, song_id):
        try:
            item = self.get_api().get(song_id)
        except Favourite.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        item["url"] = reverse("jukebox_api_favourites_item", kwargs={"song_id": item["id"]})
        return Response(data=item)

    def delete(self, request, song_id):
        try:
            return Response(data=self.get_api().remove(song_id))
        except Favourite.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ping(JukeboxAPIView):
    def get(self, request):
        return Response(data={"ping": True})
