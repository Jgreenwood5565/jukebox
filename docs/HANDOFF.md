# Handoff: jukebox modernization and Raspberry Pi deployment

This file hands work over from a cloud Claude Code session to a **local** session that can reach the
home network. Start the local session in a clone of this repository and ask Claude to read this file
first.

- Repository: `Jgreenwood5565/jukebox`, a fork of [`lociii/jukebox`](https://github.com/lociii/jukebox)
  by Jens Nistler. Leave the original repository alone and never open PRs against it.
- Branch used for the work: `claude/project-modernize-audit-30sggk`. It is merged into `master`
  (PR #1), and both point to the same code.
- State on 2026-09-24: all work is committed and pushed, CI is green, and nothing is running on the Pi yet.

## 1. What was done

The project was a 2013 Django 1.4 / Python 2 app. The work was done in these commits, all on `master`:

| Commit | What |
| --- | --- |
| `d138310` | Modernization to Python 3.10+ and Django 5.2 LTS, plus a security and bug audit |
| `56dce98` | Dark theme (default) and local username/password login |
| `c18d075` | New `README.md` with dark-mode screenshots and credits to the original author |
| `157da19` | Fix to the CI workflow (it had never run) |
| `6f47f86` | Docker image and `docker-compose.yml` for Raspberry Pi and servers |

### Modernization (`d138310`)
- Replaced `setup.py`/`requirements.txt` with `pyproject.toml`. The `jukebox` console script
  replaces `bin/jukebox`, and `./manage.py` is at the repo root.
- Django migrations replace South. `jukebox_core/migrations/0001_initial.py` produces exactly the same
  schema as the old South migrations.
- `social-auth-app-django` replaces the dead `django-social-auth`. Old `settings_local.py` names are
  translated automatically in `jukebox/settings.py`.
- jQuery 1.7 was upgraded to 3.7.1 (vendored, checked against the official hash), and
  `jukebox_web/static/js/music.js` was rewritten.
- WhiteNoise serves static files, so `DEBUG` no longer has to be on.
- New `jukebox_upgrade` command converts a 0.4 database and keeps social logins linked. It was tested
  on a simulated legacy database.
- GitHub Actions CI (`.github/workflows/ci.yml`) runs ruff, Django checks, a migration check and the
  tests on Python 3.10 and 3.13, plus a Docker build and smoke test.

### Security fixes
- **The API had no authentication at all.** The views set `permissions` instead of DRF's
  `permission_classes`, so every `/api/v1/*` endpoint was public, including `songs/skip`, which
  signals the player process.
- Every install shared the hard-coded `SECRET_KEY = "yourSecretKey"` with `DEBUG = True`. A random
  key is now generated per install at `~/.jukebox/secret_key`, mode 600.
- There was stored XSS: ID3 tags and social profile names were inserted into the page without
  escaping. Everything is escaped now.
- `songs/skip` and logout changed state on GET, which made them vulnerable to CSRF. Both are
  POST-only now.

### Bugs fixed
- `/login` redirected logged-in users to a 404.
- The RSS feed returned a random queue entry instead of the next song.
- Infinite scroll dropped the search filters after page 1.
- Removing a directory from the index also deleted sibling directories that shared the name prefix.
- The "remaining time" countdown was broken once timezones were handled.
- The vote count never updated after voting.
- Several invalid inputs returned a 500 error.
- Many N+1 query problems.

### Features added later
- **Dark theme by default**, with a Dark/Light switch in the account menu that is stored in a cookie.
  Colors are CSS variables in `jukebox_web/static/css/music.css`.
- **Local login**: a username/password form on the login page. It is on by default and turned off
  with `JUKEBOX_LOCAL_LOGIN=0`. Failed attempts are limited per IP and username: 10 attempts, then a
  15 minute lockout.
- **`jukebox jukebox_adduser <username> [--name "Full Name"] [--admin]`** creates an account or resets
  its password. Social providers are optional in `jukebox_setup`.
- German translations exist for the new strings.

### Docker (`6f47f86`)
- `Dockerfile` (python:3.13-slim) runs gunicorn as uid 1000 with 1 worker and 8 threads, runs
  migrations on start, has a health check, and stores data in the `/data` volume.
- `docker/entrypoint.sh`: `serve` (the default) starts the web server, and any other argument is
  passed to the `jukebox` CLI.
- `docker-compose.yml` plus `.env.example`: port 8000, the music folder mounted read-only at
  `/music`, and the `jukebox-data` named volume.
- Verified in the cloud session:
  - The amd64 image runs through docker compose: login, indexing and the API all work.
  - The **arm64 image was built and run under QEMU**. Every compiled dependency (`cryptography`,
    `cffi`) installed from a prebuilt aarch64 wheel, and login, indexing and the API worked.
  - 32-bit ARM (armv7) was **not** built or tested.

## 2. Verification status

- 124 tests pass: `./manage.py test`, which runs in a few seconds.
- `ruff check .` and `ruff format --check .` are clean.
- CI is green on `master`, including the Docker job.
- A Playwright end-to-end run (queue, songs, infinite scroll, sort, filters, search, vote, favourite,
  language, theme, logout, XSS payloads) passed. That script is not in the repo.

## 3. What is NOT done (open items)

1. **Nothing plays audio yet.** This is the big one. The web app only manages the queue. Playback was
   always done by separate plugins ([jukebox_mpg123](https://github.com/lociii/jukebox_mpg123),
   [jukebox_shout](https://github.com/lociii/jukebox_shout)), and those are still Python 2. The
   proposed next step is a small built-in `jukebox_play` management command that:
   - loops `api.songs().getNextSong()` → `mpg123 <Filename>`
   - registers its PID with `api.players().add(os.getpid())` and removes it on exit
   - treats **SIGABRT** as "skip the current song", because `api.songs().skipCurrentSong()` sends
     SIGABRT to every registered PID. Handle the signal and kill the running `mpg123` child.
   - runs as a second compose service `player`, sharing the `jukebox-data` volume, with the music
     mounted and `devices: ["/dev/snd:/dev/snd"]` plus the `audio` group so it can reach the Pi's
     sound card.

   The player and web containers must share the SQLite database (the same volume) **and the PID
   namespace**. Without a shared PID namespace, `os.kill` from the web container can't reach the
   player. Use `pid: "service:player"` on the web service, or run the player inside the web
   container.
2. **Upstream translations were not merged.** `lociii/jukebox` master has 8 commits this fork lacks:
   French and Brazilian Portuguese translations (`4194977`, `8a52ff7`), README and contributor
   updates, and an "Unmaintained" notice. They don't conflict functionally with this work. Merging
   was blocked in the cloud session and is the owner's decision. If wanted:
   `git fetch https://github.com/lociii/jukebox.git master`, merge it, keep this fork's
   README/settings/templates, re-add `fr` and `pt-br` to `LANGUAGES` and the language menu, then
   translate the new strings (Username, Password, or, Theme, Dark, Light, the lockout message).
3. **Upgrading an existing 0.4 install**: run `jukebox jukebox_upgrade`. Only needed if an old
   database exists somewhere.

## 4. Raspberry Pi: next steps for the local session

The owner believes the unused Pi is at an address ending in **`.4`**, probably `192.168.1.4`, though
the subnet may differ. Confirm it before touching anything, and ask the owner before installing
software or changing anything on the Pi.

### 4.1 Find and inspect the Pi (read-only)
```sh
ip route | head -3          # the local subnet, e.g. 192.168.1.0/24
ping -c 2 192.168.1.4
ssh <user>@192.168.1.4      # the user is often "pi"; ask the owner for credentials
```
Then run these on the Pi:
```sh
uname -m                    # need: aarch64 (64-bit). armv7l = 32-bit OS -> reflash with 64-bit Raspberry Pi OS
cat /proc/device-tree/model # Pi model (Pi 3/4/5 are fine)
cat /etc/os-release | head -3
free -h; df -h /            # a few hundred MB of RAM and ~1-2 GB of free disk is enough
docker --version; docker compose version
id                          # uid 1000 matches the container user
aplay -l                    # sound cards, needed for the playback work
ls <music folder>           # where the MP3s are
```
Also check that nothing already listens on port 8000 (`ss -tlnp`) and that the Pi isn't secretly in
use (`uptime`, `docker ps`, `systemctl list-units --type=service --state=running`).

### 4.2 Deploy
```sh
# only if Docker is missing (ask first):
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # then log out and back in

git clone https://github.com/Jgreenwood5565/jukebox.git
cd jukebox
cp .env.example .env
#   JUKEBOX_ALLOWED_HOSTS=<pi ip>,<pi hostname>.local,localhost
#   MUSIC_DIR=/path/to/music
#   JUKEBOX_TIME_ZONE=<owner's zone, e.g. America/New_York>
docker compose up -d --build        # the first build on a Pi takes a few minutes
docker compose ps                   # wait for "healthy"
docker compose exec jukebox jukebox jukebox_adduser <name> --admin
docker compose exec jukebox jukebox jukebox_index --path=/music
```
Open `http://<pi ip>:8000` from another device and log in. Useful commands:
- `docker compose logs -f` to follow the logs
- `git pull && docker compose up -d --build` to update
- `docker compose exec jukebox jukebox jukebox_index --path=/music` to re-index; it only adds new files

### 4.3 Deployment gotchas
- `DisallowedHost` / HTTP 400 means the address used in the browser is missing from
  `JUKEBOX_ALLOWED_HOSTS`.
- Music files must be readable by uid 1000.
- The only supported format is **MP3 with ID3 tags**. Files without an artist or title are skipped,
  and the log says so.
- The login rate limit is kept in memory per process, which is why gunicorn runs 1 worker. Keep it
  that way or configure a shared cache.
- Behind a reverse proxy with HTTPS, set `CSRF_TRUSTED_ORIGINS` (`JUKEBOX_CSRF_TRUSTED_ORIGINS`) and
  the `FORWARDED_ALLOW_IPS` environment variable for gunicorn.
- In the cloud sandbox, Docker builds needed a proxy CA workaround. That's specific to the sandbox,
  so **don't** add anything like it to the Dockerfile.

## 5. Working on the code

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
JUKEBOX_HOME=/tmp/jukebox-dev ./manage.py test
ruff check . && ruff format --check .
```
- `JUKEBOX_HOME` chooses where the database, secret key and `settings_local.py` live. The default is
  `~/.jukebox`.
- Keep the plugin API stable, because external plugins import it:
  - `jukebox.jukebox_core.api.songs().getNextSong()` returns a `Song` with `.Filename`, `.Title` and
    `.Artist.Name`
  - `api.players().add(pid)` / `.remove(pid)`
  - `FileIndexer`, importable from `jukebox.jukebox_core.management.commands.jukebox_index`
- Model fields are capitalized (`Title`, `Artist`, …) for compatibility with the existing schema, so
  don't rename them.
- Commit messages in this repo describe the why. CI must stay green. `master` has been updated by
  fast-forwarding from the work branch and through PRs inside the fork.

## 6. Key files

| Path | Purpose |
| --- | --- |
| `jukebox/settings.py` | Settings, env overrides, legacy settings translation, `settings_local.py` loading |
| `jukebox/jukebox_core/api.py` | Business logic: queue, votes, autoplay, used by the views and plugins |
| `jukebox/jukebox_core/views.py`, `urls.py` | REST API (`/api/v1/...`), docs in `jukebox_core/docs/API.rst` |
| `jukebox/jukebox_core/utils.py` | `FileIndexer`, which reads ID3 tags with mutagen |
| `jukebox/jukebox_core/management/commands/` | `jukebox_setup`, `jukebox_index`, `jukebox_adduser`, `jukebox_upgrade` |
| `jukebox/jukebox_web/` | Web UI: views (login, theme, language), templates, `static/js/music.js`, CSS |
| `Dockerfile`, `docker/entrypoint.sh`, `docker-compose.yml`, `.env.example` | Container setup |
| `README.md` | User documentation, including the Docker/Pi section |
