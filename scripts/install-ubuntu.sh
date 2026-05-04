#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Hestia — One-shot Ubuntu installer
# -----------------------------------------------------------------------------
# Run on a fresh Ubuntu 22.04 / 24.04 (Server or Desktop) machine.
#
#   curl -fsSL https://raw.githubusercontent.com/gtcolletti1/Hestia/main/scripts/install-ubuntu.sh | bash
#
# Or, if curl isn't installed yet:
#   sudo apt update && sudo apt install -y curl
#   curl -fsSL https://raw.githubusercontent.com/gtcolletti1/Hestia/main/scripts/install-ubuntu.sh | bash
#
# What it does (all idempotent — safe to re-run):
#   1. Installs OS prerequisites (curl, git, ca-certificates, gnupg, ufw)
#   2. Installs Docker Engine + Compose plugin from Docker's official repo
#   3. Adds the current user to the 'docker' group
#   4. Opens UFW for ports 22 (SSH), 80, and 443 — only if UFW is active
#   5. Clones Hestia into /opt/hestia (or git pull if already there)
#   6. Generates /opt/hestia/.env with secure random secrets
#   7. Builds and starts the full Docker Compose stack
#   8. Runs Alembic database migrations
#   9. Prints the URL to open in a browser
#
# Re-running this script is safe: it skips steps that are already done.
# -----------------------------------------------------------------------------

set -euo pipefail

REPO_URL="https://github.com/gtcolletti1/Hestia.git"
INSTALL_DIR="/opt/hestia"
RUN_USER="${SUDO_USER:-$USER}"

# ---------- Helpers ----------------------------------------------------------

C_BLUE="\033[1;34m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_RESET="\033[0m"

log()  { echo -e "${C_BLUE}==>${C_RESET} $*"; }
ok()   { echo -e "${C_GREEN}✓${C_RESET}  $*"; }
warn() { echo -e "${C_YELLOW}!${C_RESET}  $*"; }
die()  { echo -e "${C_RED}✗${C_RESET}  $*" >&2; exit 1; }

need_sudo() {
  if [[ $EUID -ne 0 ]]; then
    if ! command -v sudo >/dev/null; then
      die "This script needs sudo or root. Install sudo or re-run as root."
    fi
    if ! sudo -n true 2>/dev/null; then
      log "You'll be prompted for your sudo password..."
      sudo -v || die "sudo authentication failed"
    fi
    SUDO="sudo"
  else
    SUDO=""
  fi
}

require_ubuntu() {
  if [[ ! -f /etc/os-release ]]; then
    die "Cannot detect OS — /etc/os-release missing. This installer is for Ubuntu only."
  fi
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    die "This installer targets Ubuntu. Detected: ${ID:-unknown}. For other distros, use the manual UBUNTU_DEPLOYMENT.md guide as a reference."
  fi
  log "Detected Ubuntu ${VERSION_ID} (${VERSION_CODENAME})"
}

# ---------- Step 1: prerequisites -------------------------------------------

install_prereqs() {
  log "Installing prerequisites (curl, git, ca-certificates, gnupg, ufw)..."
  $SUDO apt-get update -qq
  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    ca-certificates curl git gnupg ufw openssl >/dev/null
  ok "Prerequisites installed."
}

# ---------- Step 2: Docker ---------------------------------------------------

install_docker() {
  # Detect snap-installed Docker — it works for hello-world but breaks Compose
  # volumes/networking in confinement. Force-replace with the apt version.
  if command -v snap >/dev/null && snap list docker >/dev/null 2>&1; then
    warn "Detected snap-installed Docker — this is incompatible with Hestia's"
    warn "Compose stack (volume mounts and networking misbehave under snap"
    warn "confinement). Removing it and installing the official apt version..."
    $SUDO snap remove docker || die "Failed to remove snap docker. Run 'sudo snap remove docker' manually and re-run this script."
  fi

  if command -v docker >/dev/null \
     && docker compose version >/dev/null 2>&1 \
     && getent group docker >/dev/null; then
    ok "Docker + Compose plugin already installed ($(docker --version | awk '{print $3}' | tr -d ','))"
    return
  fi

  log "Installing Docker Engine + Compose plugin from Docker's official apt repo..."
  $SUDO install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null

  $SUDO apt-get update -qq
  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null

  $SUDO systemctl enable --now docker >/dev/null

  ok "Docker installed: $(docker --version)"
  ok "Compose plugin: $(docker compose version)"
}

# ---------- Step 3: docker group --------------------------------------------

add_user_to_docker_group() {
  if id -nG "$RUN_USER" | grep -qw docker; then
    ok "User '$RUN_USER' is already in the docker group."
  else
    log "Adding user '$RUN_USER' to the docker group..."
    $SUDO usermod -aG docker "$RUN_USER"
    NEEDS_RELOGIN=1
  fi
}

# ---------- Step 4: firewall (only if UFW is already active) ----------------

configure_firewall() {
  if ! command -v ufw >/dev/null; then
    return
  fi
  local ufw_status
  ufw_status=$($SUDO ufw status | head -1 | awk '{print $2}')
  if [[ "$ufw_status" != "active" ]]; then
    warn "UFW is installed but not active — skipping firewall config."
    warn "  To enable later: sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable"
    return
  fi
  log "UFW is active — opening ports 22, 80, 443..."
  $SUDO ufw allow OpenSSH >/dev/null || true
  $SUDO ufw allow 80/tcp  >/dev/null || true
  $SUDO ufw allow 443/tcp >/dev/null || true
  ok "Firewall ports opened."
}

# ---------- Step 5: clone or update repo ------------------------------------

clone_or_update_repo() {
  if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    log "Cloning Hestia into $INSTALL_DIR..."
    $SUDO mkdir -p "$(dirname "$INSTALL_DIR")"
    $SUDO git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
    $SUDO chown -R "$RUN_USER:$RUN_USER" "$INSTALL_DIR"
    ok "Repository cloned."
  else
    log "Existing checkout found at $INSTALL_DIR — pulling latest..."
    sudo -u "$RUN_USER" git -C "$INSTALL_DIR" pull --ff-only
    ok "Repository up to date."
  fi
}

# ---------- Step 6: generate .env -------------------------------------------

generate_env() {
  local env_file="$INSTALL_DIR/.env"
  if [[ -f "$env_file" ]]; then
    ok ".env already exists — leaving it alone."
    return
  fi

  log "Generating $env_file with secure random secrets..."
  local pg_pw secret_key host_ip
  pg_pw=$(openssl rand -hex 24)
  secret_key=$(openssl rand -hex 32)
  host_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  host_ip=${host_ip:-127.0.0.1}

  sudo -u "$RUN_USER" cp "$INSTALL_DIR/.env.example" "$env_file"

  # Fill in the secrets (works for sed on Ubuntu's GNU sed)
  sudo -u "$RUN_USER" sed -i \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${pg_pw}|" \
    -e "s|^SECRET_KEY=.*|SECRET_KEY=${secret_key}|" \
    -e "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=[\"http://localhost\",\"http://localhost:3000\",\"http://${host_ip}\"]|" \
    "$env_file"

  chmod 600 "$env_file" 2>/dev/null || $SUDO chmod 600 "$env_file"
  ok "Generated .env (LAN IP detected: ${host_ip})"
  warn "Keep $env_file safe — it contains your DB password and app secret."
}

# ---------- Step 7: build + start --------------------------------------------

build_and_start() {
  log "Building and starting Hestia (this can take 5–15 minutes the first time)..."
  if [[ -n "${NEEDS_RELOGIN:-}" ]]; then
    # User isn't in the docker group yet for *this* shell — use sudo for compose
    cd "$INSTALL_DIR" && $SUDO docker compose up -d --build
  else
    sudo -u "$RUN_USER" bash -lc "cd '$INSTALL_DIR' && docker compose up -d --build"
  fi
  ok "Containers started."
}

# ---------- Step 8: migrations -----------------------------------------------

run_migrations() {
  log "Waiting for backend to be ready, then running database migrations..."
  local tries=0
  local compose_cmd="docker compose"
  if [[ -n "${NEEDS_RELOGIN:-}" ]]; then compose_cmd="$SUDO docker compose"; fi

  until (cd "$INSTALL_DIR" && $compose_cmd exec -T backend python -c "import app" >/dev/null 2>&1); do
    tries=$((tries + 1))
    if (( tries > 60 )); then
      warn "Backend didn't come up in 60s. You can run migrations later with:"
      warn "  cd $INSTALL_DIR && docker compose exec backend alembic upgrade head"
      return
    fi
    sleep 1
  done

  (cd "$INSTALL_DIR" && $compose_cmd exec -T backend alembic upgrade head)
  ok "Database migrations complete."
}

# ---------- Step 9: summary --------------------------------------------------

print_summary() {
  local host_ip
  host_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  host_ip=${host_ip:-localhost}

  echo
  echo -e "${C_GREEN}=========================================================${C_RESET}"
  echo -e "${C_GREEN}  Hestia is running!${C_RESET}"
  echo -e "${C_GREEN}=========================================================${C_RESET}"
  echo
  echo "  App:        http://${host_ip}/"
  echo "  API docs:   http://${host_ip}/api/docs"
  echo "  Health:     http://${host_ip}/api/health"
  echo
  echo "  Install dir: $INSTALL_DIR"
  echo "  Secrets:     $INSTALL_DIR/.env"
  echo
  echo "  Useful commands (run from $INSTALL_DIR):"
  echo "    docker compose ps              # see what's running"
  echo "    docker compose logs -f         # tail logs"
  echo "    docker compose restart backend # restart one service"
  echo "    docker compose down            # stop everything"
  echo "    git pull && docker compose up -d --build  # update"
  echo

  if [[ -n "${NEEDS_RELOGIN:-}" ]]; then
    warn "You were just added to the 'docker' group."
    warn "Log out and back in (or reboot) so you can run 'docker' without sudo."
  fi

  echo "Next: open http://${host_ip}/ on this device or any other device on your LAN."
  echo "Then go to http://${host_ip}/api/docs to create your first household + admin profile."
  echo
}

# ---------- Main -------------------------------------------------------------

main() {
  echo
  echo -e "${C_BLUE}Hestia one-shot installer for Ubuntu${C_RESET}"
  echo

  require_ubuntu
  need_sudo
  install_prereqs
  install_docker
  add_user_to_docker_group
  configure_firewall
  clone_or_update_repo
  generate_env
  build_and_start
  run_migrations
  print_summary
}

main "$@"
