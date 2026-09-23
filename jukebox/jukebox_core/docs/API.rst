API
=====

Jukebox core provides a REST API for authenticated users to control the jukebox.
Please register a Django User in the admin interface and use HTTP basic authentication for external API access.
Alternatively the API is accessible for authenticated users sending a session key. Requests authenticated by
session must send the CSRF token in the ``X-CSRFToken`` header for POST and DELETE requests.

Unauthenticated requests are rejected with status 401 or 403.

Tests
======

The API is completely unit tested. See jukebox_core/tests

GET methods
============

::

    /api/v1/songs
    /api/v1/songs/current
    /api/v1/artists
    /api/v1/albums
    /api/v1/genres
    /api/v1/years
    /api/v1/history
    /api/v1/history/my
    /api/v1/queue
    /api/v1/queue/[song_id]
    /api/v1/favourites
    /api/v1/favourites/[song_id]
    /api/v1/ping

*Sort parameters for list functions*

- order_by (field to order by, see below)
- order_direction ("asc" or "desc", defaults to "asc")

**/api/v1/songs**

List songs

*Available options*

- count (item count to be returned)
- page (page to be returned)
- search_term (search in song title, artist name and album title)
- search_title (search in song title)
- search_artist (search in artist name)
- search_album (search in album title)
- filter_artist_id (filter by artist id)
- filter_album_id (filter by album id)
- filter_genre (filter by genre id)
- filter_year (filter by release year)

*Available sort options*

- title (default, asc)
- artist
- album
- year
- genre
- length

**/api/v1/songs/current**

Get the song currently playing including its voters and the seconds remaining (``remaining``).
Returns an empty object if nothing has been played yet.

**/api/v1/artists**

List artists

*Available sort options*

- artist (default, asc)

**/api/v1/albums**

List albums

*Available sort options*

- album (default, asc)

**/api/v1/genres**

List genres

*Available sort options*

- genre (default, asc)

**/api/v1/years**

List years

*Available sort options*

- year (default, asc)

**/api/v1/history**

List all played songs

*Available sort options*

- title
- artist
- album
- year
- genre
- created (default, desc)

**/api/v1/history/my**

List all played songs the authenticated user voted for

See /api/v1/history for details

**/api/v1/queue**

List songs in play queue sorted by vote count and first vote

*Available sort options*

- title
- artist
- album
- year
- genre
- created (default, asc)
- votes (default, desc)

**/api/v1/queue/[song_id]**

Get single play queue entry

**/api/v1/favourites**

*Available sort options*

- title
- artist
- album
- year
- genre
- created (default, desc)

**/api/v1/favourites/[song_id]**

Get single favourite list entry

**/api/v1/ping**

Ping the api for session keepalive

**/feed/**

RSS feed containing the song that will be played next. Does not require authentication.

POST methods
============

::

    /api/v1/queue
    /api/v1/favourites
    /api/v1/songs/skip

**/api/v1/queue**

Vote for song, add to queue if not yet in. Responds with ``201`` and the song ``id`` and its vote ``count``,
``400`` for an invalid id and ``404`` if the song doesn't exist.

*Required post parameters*

- id (id of song to be added)

**/api/v1/favourites**

Add song to favourite list. Responds with ``201`` if the song was added and ``200`` if it already was a favourite.

*Required post parameters*

- id (id of song to be added)

**/api/v1/songs/skip**

Skip the song currently playing. Responds with ``204``.

DELETE methods
===============

::

    /api/v1/queue/[song_id]
    /api/v1/favourites/[song_id]

**/api/v1/queue/[song_id]**

Revoke vote for song, remove from queue if no more votes left. Responds with the song ``id`` and the remaining
vote ``count``.

**/api/v1/favourites/[song_id]**

Remove song from favourite list
