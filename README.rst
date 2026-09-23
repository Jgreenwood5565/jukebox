Democratic Jukebox - your democratic music player
==================================================

Ever wanted to listen to music with a larger group of people e.g. in your office? Who decides what to play?
Make your music player democratic and give everyone the chance to promote their favourite song.

Jukebox provides a web interface to search your music library and vote for songs to be played.
The more votes a song gets, the sooner you will listen to it.

At one point in your life your play queue might get empty. Don't worry, the jukebox will keep on playing.
The playback system figures out who is online using the web interface or API and plays music to their liking.

Jukebox requires Python 3.10 or newer.

.. image:: http://static.jensnistler.de/jukebox.png
   :height: 404px
   :width: 872px
   :scale: 100%
   :alt: Democratic Jukebox - your democratic music player

General
========

- Jukebox is available in english and german
- Jukebox uses Facebook, Twitter and Github for authentication (see `python-social-auth <https://python-social-auth.readthedocs.io/>`_ for more authentication providers)

Setup
==================

Install the jukebox into a virtual environment:

::

    python3 -m venv ~/jukebox-env
    source ~/jukebox-env/bin/activate
    pip install jukebox

Now it's time to configure the jukebox

1. Enter admin credentials, host names and select authentication providers
2. Create the database
3. Index your music

That's all

::

    jukebox jukebox_setup
    jukebox migrate
    jukebox jukebox_index --path=/path/to/library

Configuration, database and secret key are stored in ``~/.jukebox``. Set the ``JUKEBOX_HOME`` environment variable
to use a different directory. The configuration file ``settings_local.py`` can override every Django setting, see
``jukebox/settings_local.example.py``. ``JUKEBOX_DEBUG``, ``JUKEBOX_ALLOWED_HOSTS`` and ``JUKEBOX_SECRET_KEY``
can be set as environment variables as well.

When registering the app with your authentication provider, use ``http(s)://<your host>/complete/<provider>/``
(e.g. ``/complete/github/``) as callback URL.

The django builtin development webserver will be sufficient to serve your office or party, static files are served
by the jukebox itself. Just start it up:

::

    jukebox runserver ip:port

For a more robust setup, run ``jukebox.wsgi:application`` with any WSGI server, e.g.

::

    pip install gunicorn
    DJANGO_SETTINGS_MODULE=jukebox.settings gunicorn jukebox.wsgi:application --bind ip:port

Now you're ready to put music in the queue.

Upgrading from 0.4
------------------

Jukebox 0.5 switched from South to Django migrations and from django-social-auth to python-social-auth. Your
existing ``settings_local.py`` keeps working. Back up ``~/.jukebox/db.sqlite`` and convert the database once:

::

    jukebox jukebox_upgrade

Timestamps are now stored in UTC, entries created by older versions are displayed shifted by your UTC offset.
The playback and live indexer plugins have to be updated to Python 3 as well.

Playback
=========

Currently there are two methods of playing the music chosen in jukebox.

**shoutcast**

Stream your music to a shoutcast compatible server

::

    pip install jukebox-shout

See `jukebox_shout <https://github.com/lociii/jukebox_shout>`_ for details and startup command.

**mpg123**

Play your music locally on the machine running the jukebox.

::

    pip install jukebox-mpg123

See `jukebox_mpg123 <https://github.com/lociii/jukebox_mpg123>`_ for details and startup command.

**Contribute!**

Feel free to write additional playback modules and I'll add them to the list above.

Live indexing
===============

There is no need to update your index every time a new song is added to your library, just use the live indexer package.

::

    pip install jukebox-live-indexer

See `jukebox_live_indexer <https://github.com/lociii/jukebox_live_indexer>`_ for details and startup command.

API
=============

jukebox_core provides a fully fledged REST API for authenticated users. See `API reference <https://github.com/lociii/jukebox/blob/master/jukebox/jukebox_core/docs/API.rst>`_

Search filters
===============

Jukebox supports google-like search filter. Available search fields: title, artist, album, genre, year.

::

    title:(love to dance) artist:bobby
    artist:(bobby baby) lucky
    title:(in ten years) genre:electronic

License
========

MIT License. See `License <https://github.com/lociii/jukebox/blob/master/LICENSE.rst>`_

Contribute!
============

You want to contribute to this project? Just fork the repo and do this:

::

    git clone git@github.com:[username]/jukebox.git
    cd jukebox
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

Follow up configuring jukebox like described in Setup. Use ``./manage.py`` instead of the jukebox command.
Before sending a pull request, run the tests and the linter:

::

    ./manage.py test
    ruff check . && ruff format --check .

Release Notes
==============

0.5.0

- Python 3 and Django 5.2 LTS, Django migrations instead of South, python-social-auth instead of django-social-auth
- Security: the API now actually requires authentication, a random secret key is generated per installation,
  song metadata and user names are escaped in the web interface, jQuery updated to 3.7.1,
  skipping songs and logging out require POST
- Fixed login redirect, RSS feed picking a random instead of the next song, infinite scrolling dropping search
  filters, removed directories deleting songs of sibling directories and several crashes on invalid input
- Static files are served without DEBUG mode, new ``jukebox_upgrade`` command for existing installations

0.1.0

- Initial release

0.1.1

- Fixed installer bugs
- Added personal history
- Added system tests for api

0.2.0

- Language switch
- Sortable lists
- Google-like search operators
- Autoplay tries to play appropriate music
- Improved web interface

0.2.1

- fixed issue with autoplay

0.3.0

- Added jukebox_watch
- Added list of voters
- Minor improvements

0.3.1

- Improved exception handling
- Added rss for current song
- Minor bug fixes

0.3.2

- Update dependencies
- Fix authentication problems
- Switch from inotify to watchdog

0.3.3

- Fix manifest

0.3.4

- Fix to skip unauthorized sessions
- Updated wsgi handler

0.3.5

- Update mutagen (Thanks guys for removing old packages)
- Fixed minor bugs (Thanks to `saz <https://github.com/saz/>`_)

0.3.7

- Fix buggy pypi package

0.4.0

- Split jukebox in different packages
- Strip artist from album data

0.4.1

- Add missing wsgi file
