# Family Hub Display

A local, wall-mounted family dashboard application that shows calendars, routines, chores, lists, and meal plans. Runs on a local network (NUC/RPi + touch display in kiosk mode) and syncs with external services.

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL 16
- **Task Queue:** Celery + Redis
- **Deployment:** Docker Compose
- **Reverse Proxy:** Nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Development

```bash
# Clone and start all services
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Access the app
open http://localhost:3000
```

### Production

```bash
cp .env.example .env
# Edit .env with production values
docker compose up -d --build
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Docker Compose                       │
│                                                      │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Postgres │◄──│  FastAPI      │◄──│  Nginx       │ │
│  │  :5432   │   │  (backend)   │   │  (reverse    │ │
│  └──────────┘   │  :8000       │   │   proxy)     │ │
│                 └──────┬───────┘   │  :80 / :443  │ │
│                        │           └───────┬──────┘ │
│                 ┌──────┴───────┐           │        │
│                 │  Celery Beat │     ┌─────┴──────┐ │
│                 │  + Worker    │     │ React SPA  │ │
│                 │  (sync jobs) │     │ (static)   │ │
│                 └──────────────┘     └────────────┘ │
│                        │                            │
│                 ┌──────┴───────┐                    │
│                 │    Redis     │                    │
│                 │  (task queue │                    │
│                 │   + cache)   │                    │
│                 └──────────────┘                    │
└──────────────────────────────────────────────────────┘
```

## Project Structure

```
family-hub/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   ├── integrations/  # External API clients
│   │   └── tasks/     # Celery background tasks
│   ├── alembic/       # Database migrations
│   └── tests/
├── frontend/          # React + TypeScript SPA
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── stores/    # Zustand state management
│       └── api/       # API client
├── nginx/             # Reverse proxy config
└── docker-compose.yml
```

## Features

- **Shared family calendar** — Day/week/month views, color-coded by person
- **External calendar sync** — Google, Outlook, iCal/Apple Calendar
- **Kid-friendly routines** — Step-by-step checklists with streaks
- **Shared lists** — Grocery, to-do, packing lists
- **Meal planning** — Weekly meal view with assignments
- **Offline-first** — Fully functional without internet
- **Companion PWA** — Manage from phone when away from home
- **Home Assistant integration** — Webhooks and REST API

## Development Setup

1. **Clone the repository**

   ```bash
   git clone <repo-url> family-hub && cd family-hub
   ```

2. **Copy and edit the environment file**

   ```bash
   cp .env.example .env
   # Fill in secrets: SECRET_KEY, POSTGRES_PASSWORD, OAuth client IDs, etc.
   ```

3. **Start all services with Docker Compose (recommended)**

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

   This starts Postgres, Redis, the FastAPI backend, Celery workers, and the
   React dev server with hot-reload.

4. **Or run backend & frontend separately**

   ```bash
   # Backend
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload

   # Frontend (separate terminal)
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the app**

   - Frontend: <http://localhost:3000>
   - API docs: <http://localhost:8000/docs>

## Production Deployment

### Deploying to a Raspberry Pi or Intel NUC

1. Install Docker & Docker Compose on the target device.
2. Copy the project to the device (or `git clone`).
3. Create `.env` with production values — set strong `SECRET_KEY` and `POSTGRES_PASSWORD`.
4. Build and start:

   ```bash
   docker compose up -d --build
   ```

5. (Optional) Set up TLS by providing `TLS_CERT_PATH` and `TLS_KEY_PATH` in `.env`.
6. (Optional) Enable kiosk mode — see below.

## Kiosk Setup

The `scripts/kiosk-setup.sh` script configures a Linux device to launch Chromium in full-screen kiosk mode on boot, pointing at the local Family Hub instance.

```bash
chmod +x scripts/kiosk-setup.sh
sudo ./scripts/kiosk-setup.sh
```

What it does:

- Installs Chromium if not present
- Installs and enables a systemd service (`kiosk.service`)
- Disables screen blanking / screensaver
- Sets up a cron schedule to turn the display off at 10 PM and on at 6 AM

See `scripts/kiosk.service` for the systemd unit file, which can be customized
(e.g. changing the URL or the user).

## Backup & Restore

### Database backup

```bash
./scripts/backup.sh
```

Creates a timestamped, gzipped `pg_dump` in `backups/` and prunes backups
older than the most recent 7. Set `EXTERNAL_COPY_DIR` to also copy to
external storage.

### Database restore

```bash
./scripts/restore.sh backups/familyhub_backup_20250101_120000.sql.gz
```

Drops and recreates the database, then restores from the backup file.

### JSON export / import

```bash
# Export all tables to a portable JSON file
python scripts/export-json.py -o familyhub_export.json

# Import from JSON (skip existing rows by default)
python scripts/import-json.py familyhub_export.json

# Import with upsert (update existing rows)
python scripts/import-json.py familyhub_export.json --upsert
```

Requires `psycopg2-binary`: `pip install psycopg2-binary`.

## API Documentation

FastAPI auto-generates interactive API docs:

- **Swagger UI:** <http://localhost:8000/docs>
- **ReDoc:** <http://localhost:8000/redoc>

Both are available in development and production (served by Nginx at `/api/docs`).

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `NODE_ENV` | `production` | Environment mode |
| `DEBUG` | `false` | Enable debug logging |
| `POSTGRES_HOST` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `familyhub` | Database name |
| `POSTGRES_USER` | `familyhub` | Database user |
| `POSTGRES_PASSWORD` | — | Database password (**required**) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `BACKEND_HOST` | `0.0.0.0` | FastAPI bind host |
| `BACKEND_PORT` | `8000` | FastAPI bind port |
| `SECRET_KEY` | — | App secret for tokens & encryption (**required**) |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost` | CORS allowed origins |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost/api/integrations/google/callback` | Google OAuth redirect |
| `MICROSOFT_CLIENT_ID` | — | Microsoft OAuth client ID |
| `MICROSOFT_CLIENT_SECRET` | — | Microsoft OAuth client secret |
| `MICROSOFT_REDIRECT_URI` | `http://localhost/api/integrations/microsoft/callback` | Microsoft OAuth redirect |
| `OPENWEATHER_API_KEY` | — | OpenWeatherMap API key |
| `HOMEASSISTANT_URL` | — | Home Assistant base URL |
| `HOMEASSISTANT_TOKEN` | — | Home Assistant long-lived access token |
| `TODOIST_CLIENT_ID` | — | Todoist OAuth client ID |
| `TODOIST_CLIENT_SECRET` | — | Todoist OAuth client secret |
| `CALENDAR_SYNC_INTERVAL` | `300` | Seconds between calendar sync jobs |
| `TLS_CERT_PATH` | — | Path to TLS certificate (production) |
| `TLS_KEY_PATH` | — | Path to TLS private key (production) |

## Troubleshooting

| Problem | Solution |
|---|---|
| **Containers fail to start** | Run `docker compose logs` to check for errors. Ensure `.env` has valid `POSTGRES_PASSWORD` and `SECRET_KEY`. |
| **Database connection refused** | Verify Postgres is running: `docker compose ps`. Check `POSTGRES_HOST` matches the Docker service name (`postgres`). |
| **Calendar sync not working** | Confirm OAuth client IDs/secrets are set. Check Celery worker logs: `docker compose logs celery`. |
| **Kiosk shows blank screen** | Ensure the Docker stack is running. Check `journalctl -u kiosk -f` for Chromium errors. |
| **Touch not responding / misaligned** | See touch calibration notes in `scripts/kiosk-setup.sh`. For capacitive screens, check `display_rotate` in `/boot/config.txt`. |
| **"Permission denied" on scripts** | Run `chmod +x scripts/*.sh`. |
| **Backup fails with authentication error** | Ensure `POSTGRES_PASSWORD` is set in `.env` or exported as an environment variable. |
| **Frontend dev server won't start** | Run `npm install` in `frontend/`. Ensure Node.js 20+ is installed. |
| **Redis connection error** | Check that the Redis container is up and `REDIS_URL` is correct. |

## License

Private — All rights reserved.
