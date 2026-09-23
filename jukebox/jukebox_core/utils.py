import logging
import os
import re

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError

from .models import Album, Artist, Genre, Song

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".mp3",)


def _truncate(value, field):
    return value[: Song._meta.get_field(field).max_length]


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
            id3 = EasyID3(filename)
            length = int(MP3(filename).info.length)
        except HeaderNotFoundError:
            logger.warning("File contains invalid header data: %s", filename)
            return None
        except ID3NoHeaderError:
            logger.warning("File does not contain an id3 header: %s", filename)
            return None
        except (MutagenError, OSError) as e:
            logger.warning("Could not read %s: %s", filename, e)
            return None

        tags = {key: (values[0].strip().lower() if values else "") for key, values in id3.items()}
        artist_name = tags.get("artist")
        title = tags.get("title")
        if not artist_name or not title:
            logger.warning("Artist or title not set in %s - skipping file", filename)
            return None

        artist, _ = Artist.objects.get_or_create(Name=artist_name[:200])
        album = None
        if tags.get("album"):
            album, _ = Album.objects.get_or_create(Title=tags["album"][:200])
        genre = None
        if tags.get("genre"):
            genre, _ = Genre.objects.get_or_create(Name=tags["genre"][:200])

        return Song.objects.create(
            Artist=artist,
            Album=album,
            Genre=genre,
            Title=_truncate(title, "Title"),
            Year=_parse_year(tags.get("date")),
            Length=length,
            Filename=filename,
        )

    def delete(self, filename):
        """Remove a file, or every file below a directory, from the library."""
        Song.objects.filter(Filename=filename).delete()
        directory = filename.rstrip(os.sep) + os.sep
        Song.objects.filter(Filename__startswith=directory).delete()

    def is_indexed(self, filename):
        return Song.objects.filter(Filename=filename).exists()
