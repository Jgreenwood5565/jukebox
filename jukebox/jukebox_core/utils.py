import logging
import os
import re

import mutagen
from mutagen import MutagenError

from .models import Album, Artist, Genre, Song

logger = logging.getLogger(__name__)

# formats browsers play and mutagen reads tags of, keep in sync with
# AUDIO_CONTENT_TYPES in views.py
SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".m4a", ".ogg", ".opus")


def _truncate(value, field):
    return value[: Song._meta.get_field(field).max_length]


def _get_or_create(model, field, value):
    """Find a row ignoring case, "The Beatles" and "the beatles" are one artist."""
    value = value[:200]
    return model.objects.filter(**{f"{field}__iexact": value}).first() or model.objects.create(
        **{field: value}
    )


def _parse_year(value):
    # ID3 dates look like "2001", "2001-05" or "2001-05-03"
    match = re.match(r"\s*(\d{4})", value or "")
    return int(match.group(1)) if match else None


class FileIndexer:
    """Add music files to the library.

    Also used by the jukebox_live_indexer plugin to keep the library in sync.
    """

    def index(self, filename):
        """Index a single file, returns the new Song or None if skipped."""
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            return None

        # skip already indexed
        if self.is_indexed(filename):
            return None

        try:
            audio = mutagen.File(filename, easy=True)
        except (MutagenError, OSError) as e:
            logger.warning("Could not read %s: %s", filename, e)
            return None
        if audio is None:
            logger.warning("Unknown audio format: %s", filename)
            return None

        tags = {
            key: (values[0].strip() if values else "") for key, values in (audio.tags or {}).items()
        }
        artist_name = tags.get("artist")
        title = tags.get("title")
        if not artist_name or not title:
            logger.warning("Artist or title not set in %s - skipping file", filename)
            return None

        artist = _get_or_create(Artist, "Name", artist_name)
        album = _get_or_create(Album, "Title", tags["album"]) if tags.get("album") else None
        genre = _get_or_create(Genre, "Name", tags["genre"]) if tags.get("genre") else None

        return Song.objects.create(
            Artist=artist,
            Album=album,
            Genre=genre,
            Title=_truncate(title, "Title"),
            Year=_parse_year(tags.get("date")),
            Length=int(audio.info.length),
            Filename=filename,
        )

    def delete(self, filename):
        """Remove a file, or every file below a directory, from the library."""
        Song.objects.filter(Filename=filename).delete()
        directory = filename.rstrip(os.sep) + os.sep
        Song.objects.filter(Filename__startswith=directory).delete()

    def is_indexed(self, filename):
        return Song.objects.filter(Filename=filename).exists()
