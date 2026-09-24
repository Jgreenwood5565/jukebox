"""Cover art and browser friendly audio for the web player."""

import base64
import functools
import logging
import os
import shutil
import subprocess

import mutagen
from django.conf import settings
from mutagen.flac import Picture
from mutagen.mp4 import MP4Cover

logger = logging.getLogger(__name__)

# image files next to the music that count as its cover, e.g. "cover.jpg"
COVER_NAMES = ("cover", "folder", "front", "album", "albumart")
IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
EMBEDDED = "embedded"
FRONT_COVER = 3


def _folder_cover(filename):
    directory = os.path.dirname(filename)
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return None
    for name in names:
        stem, extension = os.path.splitext(name)
        if stem.lower() in COVER_NAMES and extension.lower() in IMAGE_TYPES:
            return os.path.join(directory, name)
    return None


def _embedded_pictures(audio):
    """Pictures in the tags as objects with ``data``, ``mime`` and ``type``."""
    # FLAC
    if getattr(audio, "pictures", None):
        return audio.pictures
    tags = audio.tags
    if tags is None:
        return []
    # ID3 (MP3)
    if hasattr(tags, "getall"):
        return tags.getall("APIC")
    # Ogg Vorbis and Opus
    if "metadata_block_picture" in tags:
        pictures = []
        for value in tags["metadata_block_picture"]:
            try:
                pictures.append(Picture(base64.b64decode(value)))
            except (ValueError, mutagen.MutagenError):
                continue
        return pictures
    return []


def _embedded_cover(filename):
    """``(data, content type)`` of the cover in the file's tags, or None."""
    try:
        audio = mutagen.File(filename)
    except (mutagen.MutagenError, OSError):
        return None
    if audio is None:
        return None

    # MP4 (M4A) stores bare images without a picture type
    covers = audio.tags.get("covr") if audio.tags is not None and "covr" in audio.tags else None
    if covers:
        cover = covers[0]
        png = cover.imageformat == MP4Cover.FORMAT_PNG
        return bytes(cover), "image/png" if png else "image/jpeg"

    pictures = _embedded_pictures(audio)
    if not pictures:
        return None
    front = next((picture for picture in pictures if picture.type == FRONT_COVER), pictures[0])
    return front.data, front.mime or "image/jpeg"


@functools.lru_cache(maxsize=2048)
def cover_source(filename):
    """Where a song's cover comes from: an image file next to it, EMBEDDED or None."""
    path = _folder_cover(filename)
    if path is not None:
        return path
    if _embedded_cover(filename) is not None:
        return EMBEDDED
    return None


def read_cover(filename):
    """``(data, content type)`` of a song's cover, or None."""
    source = cover_source(filename)
    if source is None:
        return None
    if source == EMBEDDED:
        return _embedded_cover(filename)
    try:
        with open(source, "rb") as file:
            return file.read(), IMAGE_TYPES[os.path.splitext(source)[1].lower()]
    except OSError:
        return None


@functools.lru_cache(maxsize=1)
def ffmpeg():
    path = shutil.which("ffmpeg")
    if path is None:
        logger.warning("ffmpeg not found, streaming files as they are")
    return path


def needs_transcoding(filename):
    return settings.JUKEBOX_TRANSCODE and not filename.lower().endswith(".mp3") and bool(ffmpeg())


def transcode_command(filename, start):
    return [
        ffmpeg(),
        "-nostdin",
        "-loglevel",
        "error",
        # seeking before the input is fast, it jumps instead of decoding up to there
        "-ss",
        f"{start:.2f}",
        "-i",
        filename,
        # only the audio, not the cover art FLAC files carry as a video stream
        "-map",
        "0:a:0",
        "-map_metadata",
        "-1",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "libmp3lame",
        "-b:a",
        f"{settings.JUKEBOX_TRANSCODE_BITRATE}k",
        "-f",
        "mp3",
        "pipe:1",
    ]


def transcode(filename, start=0):
    """Start converting ``filename`` to MP3 from ``start`` seconds on, returns the process."""
    return subprocess.Popen(
        transcode_command(filename, start),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
