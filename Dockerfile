# Multi-arch image (amd64, arm64 e.g. Raspberry Pi 3/4/5 with a 64-bit OS)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JUKEBOX_HOME=/data

# ffmpeg converts FLAC and other formats to MP3 for the web player
RUN apt-get update     && apt-get install -y --no-install-recommends ffmpeg     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml MANIFEST.in README.md CHANGES.txt LICENSE.rst ./
COPY jukebox ./jukebox
RUN pip install . "gunicorn>=23" \
    && rm -rf /app/jukebox

COPY docker/entrypoint.sh /usr/local/bin/jukebox-entrypoint

RUN useradd --system --uid 1000 --home-dir /data jukebox \
    && mkdir -p /data /music \
    && chown jukebox:jukebox /data
USER jukebox

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"

ENTRYPOINT ["jukebox-entrypoint"]
CMD ["serve"]
