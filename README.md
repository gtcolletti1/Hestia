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

## License

Private — All rights reserved.
