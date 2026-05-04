# Hestia — Setup Guide (macOS)

This is a step-by-step guide to get Hestia (formerly Family Hub Display) running on your Mac for **local development**.

> Deploying to a real always-on Linux host? See **[`UBUNTU_DEPLOYMENT.md`](./UBUNTU_DEPLOYMENT.md)** for a fresh-Ubuntu-Server walkthrough.

---

## Step 1: Install Docker Desktop

Docker runs the database, backend, and all services in containers so you
don't have to install PostgreSQL, Redis, or Python 3.12 yourself.

### Option A — Download installer (easiest)
1. Open: https://www.docker.com/products/docker-desktop/
2. Click **"Download for Mac"** (it auto-detects Intel vs Apple Silicon)
3. Open the downloaded `.dmg` file
4. Drag **Docker** to your **Applications** folder
5. Open Docker from Applications
6. Accept the terms and let it finish starting (you'll see the whale icon in your menu bar)

### Option B — Install Homebrew first, then Docker
```bash
# Install Homebrew (macOS package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Open Docker Desktop (first time takes a minute to initialize)
open -a Docker
```

### Verify Docker is working
Wait for the whale icon in your menu bar to stop animating, then run:
```bash
docker --version
docker compose version
```
You should see version numbers (not errors).

---

## Step 2: Set up the project

```bash
# Go to the project folder
cd ~/Projects/family-hub

# Create your local config file from the template
cp .env.example .env
```

---

## Step 3: Edit the .env file (minimum changes)

Open the `.env` file in any text editor:
```bash
open -e .env       # Opens in TextEdit
# OR
nano .env          # Edit in terminal
```

**Change these two values** (everything else can stay as-is for testing):

```
POSTGRES_PASSWORD=pick-any-password-here
SECRET_KEY=pick-any-random-string-here
```

For a proper random secret key, you can run:
```bash
openssl rand -hex 32
```
and paste the output as your SECRET_KEY.

**Leave the integration keys blank for now** (Google, Outlook, etc.) —
the app works without them, you just won't have external calendar sync yet.

Save and close the file.

---

## Step 4: Start everything

```bash
cd ~/Projects/family-hub

# Build and start all services (first time takes 3-5 minutes)
docker compose -f docker-compose.dev.yml up --build
```

**What this does:**
- Starts PostgreSQL (database)
- Starts Redis (task queue)
- Starts the FastAPI backend (Python API server)
- Starts the React frontend (Vite dev server)

**You'll see a lot of log output.** That's normal. Look for lines like:
```
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend-1  | VITE v6... ready in ... ms
frontend-1  |   ➜  Local:   http://localhost:3000/
```

---

## Step 5: Open the app

Once you see the "ready" messages:

| What | URL |
|---|---|
| **Family Hub app** | http://localhost:3000 |
| **API docs (Swagger)** | http://localhost:8000/docs |
| **API health check** | http://localhost:8000/api/health |

Open http://localhost:3000 in your browser. You should see the Family Hub
dashboard with the bottom navigation bar.

---

## Step 6: Initialize the database

The database tables need to be created. Open a **new terminal tab** (keep
Docker running in the first one):

```bash
cd ~/Projects/family-hub

# Run database migrations inside the backend container
docker compose -f docker-compose.dev.yml exec backend \
  alembic upgrade head
```

You should see Alembic walk through the migration chain ending at the current
head (e.g. `c4d8e1f72a09, notification_inbox`).

---

## Step 7: Create your first household and profile

Use the API docs to create test data. Open http://localhost:8000/docs in
your browser, then:

### Create a household:
1. Find **POST /api/households**
2. Click "Try it out"
3. Enter:
   ```json
   {"name": "The Colletti Family"}
   ```
4. Click "Execute"
5. **Copy the `id`** from the response (you'll need it)

### Create a profile:
1. Find **POST /api/profiles**
2. Click "Try it out"
3. Enter (replace `YOUR_HOUSEHOLD_ID` with the ID you copied):
   ```json
   {
     "name": "Greg",
     "color": "#3B82F6",
     "role": "admin",
     "household_id": "YOUR_HOUSEHOLD_ID"
   }
   ```
4. Click "Execute"

Now refresh http://localhost:3000 — you should see data appearing.

---

## Daily Usage

### Starting the app
```bash
cd ~/Projects/family-hub
docker compose -f docker-compose.dev.yml up
```
(No `--build` needed after the first time unless you change Dockerfiles)

### Stopping the app
Press **Ctrl+C** in the terminal where Docker is running.

Or from another terminal:
```bash
cd ~/Projects/family-hub
docker compose -f docker-compose.dev.yml down
```

### Stopping and removing all data (fresh start)
```bash
docker compose -f docker-compose.dev.yml down -v
```
The `-v` flag removes the database volume (all data is deleted).

### Viewing logs
```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Just the backend
docker compose -f docker-compose.dev.yml logs -f backend

# Just the frontend
docker compose -f docker-compose.dev.yml logs -f frontend
```

---

## Troubleshooting

### "port is already in use"
Something else is using port 3000, 5432, 6379, or 8000. Find and stop it:
```bash
lsof -i :3000    # See what's using port 3000
# Then kill the process, or change the port in docker-compose.dev.yml
```

### "Docker is not running"
Open Docker Desktop from Applications. Wait for the whale icon to
stop animating.

### "Cannot connect to the Docker daemon"
Same as above — Docker Desktop needs to be running first.

### Frontend shows blank page
Check the browser console (Cmd+Option+J) for errors. Make sure the
backend is running (check http://localhost:8000/api/health).

### Database connection error
Make sure PostgreSQL started successfully:
```bash
docker compose -f docker-compose.dev.yml ps
```
All services should show "Up" or "running".

---

## Optional: Set up external integrations

These are **not required** for testing — the app works fully with
local-only data.

### Google Calendar
1. Go to https://console.cloud.google.com/
2. Create a project → Enable Google Calendar API
3. Create OAuth 2.0 credentials (Web application)
4. Set redirect URI to: `http://localhost:8000/api/integrations/oauth/google/callback`
5. Copy Client ID and Secret into your `.env` file

### OpenWeatherMap (weather widget)
1. Go to https://openweathermap.org/api
2. Sign up for a free account
3. Copy your API key into `OPENWEATHER_API_KEY` in `.env`

### Todoist
1. Go to https://developer.todoist.com/
2. Create an app
3. Copy Client ID and Secret into `.env`

After changing `.env`, restart Docker:
```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up
```
