#!/bin/sh
set -e

case "$1" in
    serve)
        jukebox migrate --noinput
        # one process keeps the login rate limit consistent, threads handle concurrency
        exec gunicorn jukebox.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers 1 \
            --threads "${GUNICORN_THREADS:-8}" \
            --access-logfile - \
            --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
        ;;
    *)
        # any other command is passed to the jukebox cli, e.g. "jukebox_index --path=/music"
        exec jukebox "$@"
        ;;
esac
