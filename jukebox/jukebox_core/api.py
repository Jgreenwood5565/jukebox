"""Jukebox business logic shared by the REST API and the playback plugins.

Playback plugins (jukebox_shout, jukebox_mpg123, ...) rely on ``songs``,
``players`` and their camelCase methods, keep those names stable.
"""

import os
import re
import time
from collections import Counter
from signal import SIGABRT

from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, Paginator
from django.db import transaction
from django.db.models import Count, Min, Q
from django.utils import formats, timezone

from .models import Album, Artist, Favourite, Genre, History, Player, Queue, Song

SEARCH_KEYWORDS = ("title", "artist", "album", "genre", "year")

SONG_RELATED = ("Artist", "Album", "Genre")


def parse_search_string(keywords, term):
    """Split a search string into ``keyword:value`` options and free text.

    Values containing whitespace can be wrapped in brackets, e.g.
    ``artist:(the beatles) yesterday``. Returns a dict with one entry per
    keyword found plus ``term`` holding the remaining text.
    """
    values = {}
    for keyword in keywords:
        match = re.search(r"(?:^|\s)" + re.escape(keyword) + ":", term)
        if match is None:
            continue

        start = match.end()
        if term.startswith("(", start):
            end = len(term)
            depth = 0
            for pos in range(start, len(term)):
                if term[pos] == "(":
                    depth += 1
                elif term[pos] == ")":
                    depth -= 1
                    if depth == 0:
                        end = pos + 1
                        break
            value = term[start + 1 : end]
            if value.endswith(")"):
                value = value[:-1]
        else:
            end = term.find(" ", start)
            if end == -1:
                end = len(term)
            value = term[start:end]

        values[keyword] = value
        term = term[: match.start()] + " " + term[end:]

    values["term"] = re.sub(r"\s+", " ", term).strip()
    return values


def _bracket(value):
    return f"({value})" if " " in value else value


def _user_data(user):
    return {"id": user.id, "name": user.get_full_name() or user.get_username()}


def song_data(song):
    """Serialize a song in the format shared by all list endpoints."""
    return {
        "id": song.id,
        "title": song.Title,
        "artist": {
            "id": song.Artist.id if song.Artist else None,
            "name": song.Artist.Name if song.Artist else None,
        },
        "album": {
            "id": song.Album.id if song.Album else None,
            "title": song.Album.Title if song.Album else None,
        },
        "year": song.Year,
        "genre": {
            "id": song.Genre.id if song.Genre else None,
            "name": song.Genre.Name if song.Genre else None,
        },
        "queued": False,
        "favourite": False,
    }


def _voted_song_data(item):
    """Serialize a queue or history entry including its voters."""
    users = list(item.User.all())
    dataset = song_data(item.Song)
    dataset.update(
        {
            "created": formats.date_format(timezone.localtime(item.Created), "DATETIME_FORMAT"),
            "votes": len(users),
            "users": [_user_data(user) for user in users],
        }
    )
    return dataset


class api_base:
    count = 30
    order_by_fields = {}
    order_by_directions = ("asc", "desc")
    order_by_default = None
    result_type = None

    def __init__(self):
        self.user_id = None
        self.search_term = None
        self.search_title = None
        self.search_artist_name = None
        self.search_album_title = None
        self.filter_year = None
        self.filter_genre = None
        self.filter_album_id = None
        self.filter_artist_id = None
        self.order_by_field = None
        self.order_by_direction = None

    def set_count(self, count):
        if count > 100:
            self.count = 100
        elif count > 0:
            self.count = count

    def set_user_id(self, user_id):
        self.user_id = user_id

    def set_search_term(self, term):
        options = parse_search_string(SEARCH_KEYWORDS, term)
        for key, value in options.items():
            if key == "title":
                self.set_search_title(value)
            elif key == "artist":
                self.set_search_artist_name(value)
            elif key == "album":
                self.set_search_album_title(value)
            elif key == "genre":
                genre = Genre.objects.filter(Name__iexact=value).first()
                if genre is not None:
                    self.set_filter_genre(genre.id)
            elif key == "year":
                try:
                    self.set_filter_year(int(value))
                except ValueError:
                    pass

        self.search_term = options["term"] or None

    # kept for backwards compatibility
    def parseSearchString(self, keywords, term):  # noqa: N802
        return parse_search_string(keywords, term)

    def set_search_title(self, term):
        self.search_title = term

    def set_search_artist_name(self, term):
        self.search_artist_name = term

    def set_search_album_title(self, term):
        self.search_album_title = term

    def set_filter_year(self, term):
        self.filter_year = term

    def set_filter_genre(self, term):
        self.filter_genre = term

    def set_filter_album_id(self, term):
        self.filter_album_id = term

    def set_filter_artist_id(self, term):
        self.filter_artist_id = term

    def set_order_by(self, field, direction="asc"):
        if field not in self.order_by_fields or direction not in self.order_by_directions:
            return

        self.order_by_field = field
        self.order_by_direction = direction

    def get_default_result(self, result_type, page):
        search = {}
        if self.search_title is not None:
            search["title"] = _bracket(self.search_title)
        if self.search_artist_name is not None:
            search["artist"] = _bracket(self.search_artist_name)
        if self.search_album_title is not None:
            search["album"] = _bracket(self.search_album_title)
        if self.filter_genre is not None:
            genre = Genre.objects.filter(id=self.filter_genre).first()
            if genre is not None:
                search["genre"] = _bracket(genre.Name)
                search["genre_id"] = genre.id
        if self.filter_year is not None:
            search["year"] = str(self.filter_year)
        if self.search_term is not None:
            search["term"] = self.search_term

        return {
            "type": result_type,
            "page": page,
            "hasNextPage": False,
            "itemList": [],
            "order": [],
            "search": search,
        }

    def mark_queued_and_favourites(self, datasets):
        """Flag songs the current user voted for or marked as favourite."""
        if self.user_id is None or not datasets:
            return datasets

        song_ids = [dataset["id"] for dataset in datasets]
        queued = set(
            Queue.objects.filter(Song__in=song_ids, User__id=self.user_id).values_list(
                "Song", flat=True
            )
        )
        favourites = set(
            Favourite.objects.filter(Song__in=song_ids, User__id=self.user_id).values_list(
                "Song", flat=True
            )
        )
        for dataset in datasets:
            dataset["queued"] = dataset["id"] in queued
            dataset["favourite"] = dataset["id"] in favourites
        return datasets

    def result_add_queue_and_favourite(self, song, dataset):
        return self.mark_queued_and_favourites([dataset])[0]

    def source_set_order(self, object_list):
        if self.order_by_field is not None:
            field_name = self.order_by_fields[self.order_by_field]
            if self.order_by_direction == "desc":
                field_name = "-" + field_name
            return object_list.order_by(field_name)
        if self.order_by_default is not None:
            return object_list.order_by(*self.order_by_default.values())
        return object_list

    def result_set_order(self, result):
        result["order"] = []

        if self.order_by_field is not None:
            result["order"].append(
                {
                    "field": self.order_by_field,
                    "direction": self.order_by_direction,
                }
            )
        elif self.order_by_default is not None:
            for field, order in self.order_by_default.items():
                result["order"].append(
                    {
                        "field": field,
                        "direction": "desc" if order.startswith("-") else "asc",
                    }
                )

        return result

    def build_result(self, object_list, page, serialize, result_type=None):
        """Paginate ``object_list`` and serialize the requested page."""
        result = self.get_default_result(result_type or self.result_type, page)
        result = self.result_set_order(result)

        try:
            page_obj = Paginator(object_list, self.count).page(page)
        except InvalidPage:
            return result

        result["hasNextPage"] = page_obj.has_next()
        result["itemList"] = [serialize(item) for item in page_obj.object_list]
        return result


class songs(api_base):
    result_type = "songs"
    order_by_fields = {
        "title": "Title",
        "artist": "Artist__Name",
        "album": "Album__Title",
        "year": "Year",
        "genre": "Genre__Name",
        "length": "Length",
    }
    order_by_default = {
        "title": "Title",
    }

    def index(self, page=1):
        object_list = Song.objects.select_related(*SONG_RELATED)

        # searches
        if self.search_term is not None:
            object_list = object_list.filter(
                Q(Title__icontains=self.search_term)
                | Q(Artist__Name__icontains=self.search_term)
                | Q(Album__Title__icontains=self.search_term)
            )
        if self.search_title is not None:
            object_list = object_list.filter(Title__icontains=self.search_title)
        if self.search_artist_name is not None:
            object_list = object_list.filter(Artist__Name__icontains=self.search_artist_name)
        if self.search_album_title is not None:
            object_list = object_list.filter(Album__Title__icontains=self.search_album_title)

        # filters
        if self.filter_year is not None:
            object_list = object_list.filter(Year=self.filter_year)
        if self.filter_genre is not None:
            object_list = object_list.filter(Genre=self.filter_genre)
        if self.filter_album_id is not None:
            object_list = object_list.filter(Album=self.filter_album_id)
        if self.filter_artist_id is not None:
            object_list = object_list.filter(Artist=self.filter_artist_id)

        object_list = self.source_set_order(object_list)

        def serialize(song):
            dataset = song_data(song)
            dataset["length"] = song.Length
            return dataset

        result = self.build_result(object_list, page, serialize)
        self.mark_queued_and_favourites(result["itemList"])
        return result

    def getNextSong(self):  # noqa: N802
        """Pop the next song to play and record it in the history.

        Takes the most voted song from the queue, falling back to a song the
        currently active listeners are likely to enjoy, then to a random one.
        Songs whose file vanished are removed from the library and skipped.
        Raises ``Song.DoesNotExist`` if the library is empty.
        """
        while True:
            with transaction.atomic():
                queue_item = (
                    Queue.objects.select_related("Song__Artist")
                    .annotate(VoteCount=Count("User"), MinCreated=Min("Created"))
                    .order_by("-VoteCount", "MinCreated")
                    .first()
                )
                if queue_item is not None:
                    song_instance = queue_item.Song
                else:
                    try:
                        song_instance = self.getRandomSongByPreferences()
                    except ObjectDoesNotExist:
                        song_instance = self.getRandomSong()

                if not os.path.exists(song_instance.Filename):
                    # also removes its queue entry
                    song_instance.delete()
                    continue

                if queue_item is not None:
                    self.addToHistory(song_instance, queue_item.User)
                    queue_item.delete()
                else:
                    self.addToHistory(song_instance, None)

            return song_instance

    def getRandomSong(self):  # noqa: N802
        song_instance = Song.objects.select_related("Artist").order_by("?").first()
        if song_instance is None:
            raise Song.DoesNotExist("The music library is empty")
        return song_instance

    def getRandomSongByPreferences(self):  # noqa: N802
        # users with an active web session
        user_ids = set()
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            user_id = session.get_decoded().get("_auth_user_id")
            if user_id is not None:
                user_ids.add(user_id)

        # artists of their newest favourites and recently voted songs
        artists = Counter()
        for user_id in user_ids:
            artists.update(
                Favourite.objects.filter(User__id=user_id).values_list("Song__Artist", flat=True)[
                    :30
                ]
            )
            artists.update(
                History.objects.filter(User__id=user_id).values_list("Song__Artist", flat=True)[:30]
            )

        # nothing played and no favourites
        if not artists:
            raise Song.DoesNotExist("No listener preferences available")

        top_artists = [artist_id for artist_id, _ in artists.most_common(30)]
        last_played = list(History.objects.values_list("Song", flat=True)[:50])

        # find a song not played recently
        song_instance = (
            Song.objects.select_related("Artist")
            .exclude(id__in=last_played)
            .filter(Artist__in=top_artists)
            .order_by("?")
            .first()
        )
        if song_instance is None:
            raise Song.DoesNotExist("No matching song found")
        return song_instance

    def addToHistory(self, song_instance, user_list):  # noqa: N802
        history_instance = History.objects.create(Song=song_instance)
        if user_list is not None:
            users = user_list.all() if hasattr(user_list, "all") else user_list
            history_instance.User.add(*users)
        return history_instance

    def skipCurrentSong(self):  # noqa: N802
        for player in Player.objects.all():
            try:
                os.kill(player.Pid, SIGABRT)
            except OSError:
                # player process is gone
                player.delete()


class history(api_base):
    result_type = "history"
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
    }
    order_by_default = {
        "created": "-Created",
    }

    def get_queryset(self):
        return History.objects.all()

    def index(self, page=1):
        object_list = (
            self.get_queryset()
            .select_related(*(f"Song__{name}" for name in SONG_RELATED))
            .prefetch_related("User")
        )
        object_list = self.source_set_order(object_list)
        result = self.build_result(object_list, page, _voted_song_data)
        self.mark_queued_and_favourites(result["itemList"])
        return result

    def getCurrent(self):  # noqa: N802
        item = (
            History.objects.select_related(*(f"Song__{name}" for name in SONG_RELATED))
            .prefetch_related("User")
            .first()
        )
        if item is None:
            raise History.DoesNotExist("Nothing played yet")

        dataset = _voted_song_data(item)
        dataset["remaining"] = int(item.Created.timestamp() + item.Song.Length - time.time())
        return dataset


class history_my(history):
    result_type = "history/my"

    def get_queryset(self):
        return History.objects.filter(User__id=self.user_id)


class queue(api_base):
    result_type = "queue"
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
        "votes": "VoteCount",
    }
    order_by_default = {
        "votes": "-VoteCount",
        "created": "MinCreated",
    }

    def get_queryset(self):
        return (
            Queue.objects.select_related(*(f"Song__{name}" for name in SONG_RELATED))
            .prefetch_related("User")
            .annotate(VoteCount=Count("User"), MinCreated=Min("Created"))
        )

    def index(self, page=1):
        object_list = self.source_set_order(self.get_queryset())
        result = self.build_result(object_list, page, _voted_song_data)
        self.mark_queued_and_favourites(result["itemList"])
        return result

    def get(self, song_id):
        item = self.get_queryset().get(Song__id=song_id)
        return self.mark_queued_and_favourites([_voted_song_data(item)])[0]

    def add(self, song_id):
        """Vote for a song, returns the number of votes it has now."""
        song = Song.objects.get(id=song_id)
        with transaction.atomic():
            queue_item, _ = Queue.objects.get_or_create(Song=song)
            queue_item.User.add(self.user_id)
            return queue_item.User.count()

    def remove(self, song_id):
        with transaction.atomic():
            queue_item = Queue.objects.select_for_update().get(Song__id=song_id)
            queue_item.User.remove(self.user_id)
            vote_count = queue_item.User.count()
            if not vote_count:
                queue_item.delete()

        return {
            "id": int(song_id),
            "count": vote_count,
        }


class favourites(api_base):
    result_type = "favourites"
    order_by_fields = {
        "title": "Song__Title",
        "artist": "Song__Artist__Name",
        "album": "Song__Album__Title",
        "year": "Song__Year",
        "genre": "Song__Genre__Name",
        "created": "Created",
    }
    order_by_default = {
        "created": "-Created",
    }

    def get_queryset(self):
        return Favourite.objects.filter(User__id=self.user_id).select_related(
            *(f"Song__{name}" for name in SONG_RELATED)
        )

    def serialize(self, item):
        dataset = song_data(item.Song)
        dataset["created"] = formats.date_format(
            timezone.localtime(item.Created), "DATETIME_FORMAT"
        )
        return dataset

    def index(self, page=1):
        object_list = self.source_set_order(self.get_queryset())
        result = self.build_result(object_list, page, self.serialize)
        self.mark_queued_and_favourites(result["itemList"])
        return result

    def get(self, song_id):
        item = self.get_queryset().get(Song__id=song_id)
        return self.mark_queued_and_favourites([self.serialize(item)])[0]

    def add(self, song_id):
        """Mark a song as favourite, returns True if it was newly added."""
        song = Song.objects.get(id=song_id)
        _, created = Favourite.objects.get_or_create(Song=song, User_id=self.user_id)
        return created

    def remove(self, song_id):
        self.get_queryset().get(Song__id=song_id).delete()

        return {
            "id": int(song_id),
        }


class artists(api_base):
    result_type = "artists"
    order_by_fields = {
        "artist": "Name",
    }
    order_by_default = {
        "artist": "Name",
    }

    def index(self, page=1):
        object_list = self.source_set_order(Artist.objects.all())
        return self.build_result(
            object_list, page, lambda item: {"id": item.id, "artist": item.Name}
        )


class albums(api_base):
    result_type = "albums"
    order_by_fields = {
        "album": "Title",
    }
    order_by_default = {
        "album": "Title",
    }

    def index(self, page=1):
        object_list = self.source_set_order(Album.objects.all())
        return self.build_result(
            object_list, page, lambda item: {"id": item.id, "album": item.Title}
        )


class genres(api_base):
    result_type = "genres"
    order_by_fields = {
        "genre": "Name",
    }
    order_by_default = {
        "genre": "Name",
    }

    def index(self, page=1):
        object_list = self.source_set_order(Genre.objects.all())
        return self.build_result(
            object_list, page, lambda item: {"id": item.id, "genre": item.Name}
        )


class years(api_base):
    result_type = "years"
    order_by_fields = {
        "year": "Year",
    }
    order_by_default = {
        "year": "Year",
    }

    def index(self, page=1):
        object_list = Song.objects.values("Year").exclude(Year=None).exclude(Year=0).distinct()
        object_list = self.source_set_order(object_list)
        return self.build_result(object_list, page, lambda item: {"year": item["Year"]})


class players(api_base):
    def add(self, pid):
        return Player.objects.create(Pid=pid).id

    def remove(self, pid):
        Player.objects.filter(Pid=pid).delete()

        return {
            "pid": pid,
        }
