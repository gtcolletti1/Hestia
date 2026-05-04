# Hestia — Ubuntu Deployment Guide

End-to-end walkthrough for deploying Hestia (Family Hub Display) on a **fresh
Ubuntu 22.04 / 24.04 LTS Server** install. Works on Intel NUC, generic mini PC,
a VM, or a Raspberry Pi 4/5 running Ubuntu Server (arm64).

What you'll end up with:
- Hestia running under Docker Compose (Postgres, Redis, FastAPI backend,
  Celery worker + beat, React SPA built and served by Nginx).
- Reachable on your LAN at `http://<host-ip>/`.
- Auto-start on boot, with a nightly database backup.
- Optional: TLS, kiosk-mode browser on the same box.

---

## 0. Before you start

You need:
- A machine with **Ubuntu Server 22.04 LTS or 24.04 LTS** installed
  (`ubuntu-server-22.04.x-live-server-amd64.iso` or the arm64 image for Pi).
- A **non-root user with `sudo`** privileges (created during the OS installer).
- The machine on your LAN with an IP you can reach via SSH.
- A **GitHub Personal Access Token (classic)** with `repo` scope if the
  repository is private. (You don't need this for a public repo.)
- 2 GB RAM minimum, 4 GB recommended. ~5 GB free disk.

Find your server's IP if you don't know it:
```bash
ip -4 addr show | grep inet
```

SSH to it from your workstation:
```bash
ssh youruser@192.168.1.50    # replace with your IP
```

Everything below runs **on the Ubuntu host**.

---

## 1. Update the OS

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg git ufw unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades   # accept defaults
```

Reboot if a kernel update was applied:
```bash
sudo reboot
```

---

## 2. Install Docker Engine + Compose plugin

Use Docker's official apt repository — the `docker.io` package in Ubuntu's
default repos is older and can lag behind on Compose v2.

> **Heads up:** Ubuntu Desktop's "minimal install" option (and some cloud
> images) ships without `curl`. If Step 1 was skipped or partially applied,
> run this first or you'll get `Command 'curl' not found`:
> ```bash
> sudo apt update && sudo apt -y install curl ca-certificates gnupg git
> ```

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Let your user run `docker` without `sudo`:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verify:
```bash
docker --version
docker compose version
docker run --rm hello-world
```

---

## 3. Open the firewall

The stack publishes ports `80` (Nginx) and, if you enable TLS, `443`.
SSH (`22`) needs to stay open so you don't lock yourself out.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

> **Wall display only?** If this machine sits next to the wall display and is
> never accessed from another device, you can skip the firewall entirely.

---

## 4. Clone the repository

Pick a stable home for the deployment. `/opt/hestia` is a common choice.

```bash
sudo mkdir -p /opt/hestia
sudo chown $USER:$USER /opt/hestia
cd /opt
git clone https://github.com/gtcolletti1/Hestia.git hestia
cd hestia
```

> **Private repo?** Use a Personal Access Token:
> ```bash
> git clone https://<USERNAME>:<TOKEN>@github.com/gtcolletti1/Hestia.git hestia
> ```
> or set up SSH keys (`ssh-keygen -t ed25519`, add the public key under
> *GitHub → Settings → SSH and GPG keys*) and clone via
> `git@github.com:gtcolletti1/Hestia.git`.

---

## 5. Configure `.env`

```bash
cp .env.example .env
nano .env       # or: vim .env
```

**Required changes (do not skip):**

```env
POSTGRES_PASSWORD=<long random string, no spaces>
SECRET_KEY=<paste output of: openssl rand -hex 32>
ALLOWED_ORIGINS=["http://192.168.1.50","http://hestia.local"]
```

Generate a secret in another terminal:
```bash
openssl rand -hex 32
```

Replace `192.168.1.50` with the actual LAN IP of this host. Add any
additional hostnames you'll use (e.g. `hestia.local` if you set up mDNS).

**Leave the integration keys blank for now** — Google, Microsoft, OpenWeatherMap,
Todoist. Hestia runs fully without them; add them later via Settings or by
editing `.env` and restarting.

Save and close.

---

## 6. Build and start the stack

First build (downloads base images and compiles the frontend, ~5–10 min on a
NUC, longer on a Pi):

```bash
cd /opt/hestia
docker compose up -d --build
```

Watch it come up:
```bash
docker compose ps
docker compose logs -f
```
Press `Ctrl+C` to stop tailing logs (the containers keep running).

You should see all six services healthy: `postgres`, `redis`, `backend`,
`celery-worker`, `celery-beat`, `frontend`, `nginx`.

---

## 7. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

Expect output ending in something like
`INFO  [alembic.runtime.migration] Running upgrade … -> c4d8e1f72a09, notification_inbox`.

---

## 8. Open the app

From any device on the same LAN:

```
http://<your-server-ip>/
```

You should see Hestia's splash screen. Tap/click to log in.

API health check:
```
http://<your-server-ip>/api/health
```

---

## 9. Create your first household + admin profile

Easiest path: open the API docs in a browser.

```
http://<your-server-ip>/api/docs
```

1. **POST `/api/households`** with `{"name": "The Smith Family"}` → copy the returned `id`.
2. **POST `/api/profiles`** with:
   ```json
   {
     "name": "Greg",
     "color": "#3B82F6",
     "role": "admin",
     "household_id": "<paste id from step 1>"
   }
   ```
3. Refresh the splash → you should now see your profile in the picker.

(You can do all of this later from the in-app Settings panel once an admin
profile exists.)

---

## 10. Make it survive reboots

Docker containers with `restart: unless-stopped` (already set in
`docker-compose.yml`) will come back automatically as long as the Docker
service starts on boot:

```bash
sudo systemctl enable docker
```

Reboot and confirm:
```bash
sudo reboot
# wait, then SSH back in
docker compose -f /opt/hestia/docker-compose.yml ps
```

---

## 11. Nightly database backup (cron)

```bash
crontab -e
```

Add:
```
0 2 * * * cd /opt/hestia && ./scripts/backup.sh >> /var/log/hestia-backup.log 2>&1
```

This keeps the most recent 7 gzipped `pg_dump` backups in
`/opt/hestia/backups/`. Set `EXTERNAL_COPY_DIR` in `.env` to also mirror to a
USB drive or mounted NAS share.

Make the log file writable:
```bash
sudo touch /var/log/hestia-backup.log
sudo chown $USER:$USER /var/log/hestia-backup.log
```

You can also do **JSON exports** (portable, vendor-neutral) from the in-app
Settings → System → Backup & Restore panel.

---

## 12. (Optional) TLS with a self-signed cert for LAN

For a true public hostname, use Let's Encrypt — out of scope here. For LAN-only
"https://hestia.local" with a trust prompt:

```bash
sudo mkdir -p /etc/hestia/tls
sudo openssl req -x509 -nodes -days 825 \
  -newkey rsa:2048 \
  -keyout /etc/hestia/tls/hestia.key \
  -out    /etc/hestia/tls/hestia.crt \
  -subj "/CN=hestia.local" \
  -addext "subjectAltName=DNS:hestia.local,IP:192.168.1.50"
sudo chmod 640 /etc/hestia/tls/*
```

In `.env`:
```env
TLS_CERT_PATH=/etc/hestia/tls/hestia.crt
TLS_KEY_PATH=/etc/hestia/tls/hestia.key
```

Then restart Nginx:
```bash
docker compose up -d nginx
```

---

## 13. (Optional) Kiosk mode on the same box

If this Ubuntu machine *is* your wall display:

```bash
cd /opt/hestia
chmod +x scripts/kiosk-setup.sh
sudo ./scripts/kiosk-setup.sh
```

Installs Chromium, registers a `kiosk.service` systemd unit, and disables
screen blanking. Edit `scripts/kiosk.service` first if you want to point at a
different URL or run as a different user.

---

## 14. Updating Hestia from GitHub

```bash
cd /opt/hestia
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

If the frontend or nginx config changed, the rebuild picks it up automatically
because the production images COPY rather than bind-mount. If only the SPA
changed, you can target it: `docker compose build frontend && docker compose up -d frontend`.

To check what changed:
```bash
git log --oneline HEAD@{1}..HEAD
```

---

## 15. Day-to-day operations

| Task | Command |
|---|---|
| Status of all services | `docker compose ps` |
| Tail all logs | `docker compose logs -f` |
| Tail one service | `docker compose logs -f backend` |
| Restart one service | `docker compose restart backend` |
| Stop everything | `docker compose down` |
| Stop and **delete the database volume** | `docker compose down -v` (destructive!) |
| Open a Postgres shell | `docker compose exec postgres psql -U $POSTGRES_USER $POSTGRES_DB` |
| Run a backend Python shell | `docker compose exec backend python` |
| Show disk usage of Docker | `docker system df` |
| Reclaim space (safe) | `docker system prune -f` |

All commands assume `cd /opt/hestia` first.

---

## 16. Troubleshooting

**`permission denied` on `/var/run/docker.sock`** — your shell hasn't picked
up the `docker` group yet. Run `newgrp docker` or log out and back in.

**`bind: address already in use` on port 80** — something else (Apache, the
default `nginx` apt package, another container) is on port 80.
`sudo ss -tulpn | grep ':80 '` to find it, then stop or remove it.

**`alembic upgrade head` fails with "relation already exists"** — the database
was previously initialized by a different mechanism. Drop the volume and start
clean: `docker compose down -v && docker compose up -d --build && docker compose exec backend alembic upgrade head`.

**Frontend loads but every API call 502s** — Nginx is up but the backend isn't
ready. `docker compose logs backend` — the most common cause is a wrong
`POSTGRES_PASSWORD` or `SECRET_KEY` not set.

**Pi or low-RAM box OOMs during build** — build the frontend on a beefier
machine (or use the prebuilt image if you publish one) and `docker compose pull`
on the Pi instead of `--build`. Alternatively add a swap file:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Service worker cached an old version** — bump `CACHE_VERSION` in
`frontend/public/service-worker.js`, rebuild the frontend, and reload in the
browser. The `/service-worker.js` and `/manifest.json` paths are explicitly
served `Cache-Control: no-cache` by Nginx so updates roll out cleanly.

**Need to start completely over** —
```bash
cd /opt/hestia
docker compose down -v
docker compose up -d --build
docker compose exec backend alembic upgrade head
```
This wipes the database. Backups in `./backups/` are not touched.

---

## 17. Where things live

| Path | What |
|---|---|
| `/opt/hestia/` | Source checkout (this is what `git pull` updates) |
| `/opt/hestia/.env` | Local secrets — **back this up; it's not in git** |
| `/opt/hestia/backups/` | Nightly `pg_dump` archives |
| Docker volume `hestia_pgdata` | The actual Postgres data files |
| Docker volume `hestia_upload_photos` | Uploaded splash/photo-frame images |

To back up the secrets file:
```bash
cp /opt/hestia/.env ~/hestia.env.backup
```

---

## 18. Uninstall

```bash
cd /opt/hestia
docker compose down -v
cd ..
sudo rm -rf /opt/hestia
docker volume prune -f
sudo apt -y remove docker-ce docker-ce-cli containerd.io   # only if Docker isn't used for anything else
```

---

You're done. The full PRD is in
[`PRD_Family_Hub_Display_v2.md`](./PRD_Family_Hub_Display_v2.md), and the
README has the configuration reference.
