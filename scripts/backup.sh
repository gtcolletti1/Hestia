#!/usr/bin/env bash
# =============================================================================
# Family Hub — Database Backup
# Creates a timestamped, gzipped PostgreSQL dump and prunes old backups.
# =============================================================================
set -euo pipefail

# --- Configuration (override via env vars or .env file) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "${ENV_FILE}" ]]; then
    # Source only POSTGRES_* variables from .env
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^POSTGRES_' "${ENV_FILE}")
    set +a
fi

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGDATABASE="${POSTGRES_DB:-familyhub}"
PGUSER="${POSTGRES_USER:-familyhub}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"

export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD

BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
EXTERNAL_COPY_DIR="${EXTERNAL_COPY_DIR:-}"   # e.g. /mnt/usb/family-hub-backups
MAX_BACKUPS="${MAX_BACKUPS:-7}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FILENAME="familyhub_backup_${TIMESTAMP}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

echo "=== Family Hub Database Backup ==="
echo "Host:     ${PGHOST}:${PGPORT}"
echo "Database: ${PGDATABASE}"
echo "Output:   ${FILEPATH}"
echo ""

# --- Dump & compress ---
echo ">> Creating backup..."
pg_dump --format=plain --no-owner --no-acl | gzip > "${FILEPATH}"
echo ">> Backup created: ${FILEPATH} ($(du -h "${FILEPATH}" | cut -f1))"

# --- Prune old backups ---
BACKUP_COUNT="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'familyhub_backup_*.sql.gz' | wc -l | tr -d ' ')"
if (( BACKUP_COUNT > MAX_BACKUPS )); then
    DELETE_COUNT=$(( BACKUP_COUNT - MAX_BACKUPS ))
    echo ">> Pruning ${DELETE_COUNT} old backup(s) (keeping ${MAX_BACKUPS})..."
    # shellcheck disable=SC2012
    ls -1t "${BACKUP_DIR}"/familyhub_backup_*.sql.gz | tail -n "${DELETE_COUNT}" | xargs rm -f
fi

# --- Optional: copy to external storage ---
if [[ -n "${EXTERNAL_COPY_DIR}" ]]; then
    if [[ -d "${EXTERNAL_COPY_DIR}" ]]; then
        cp "${FILEPATH}" "${EXTERNAL_COPY_DIR}/"
        echo ">> Copied to external storage: ${EXTERNAL_COPY_DIR}/${FILENAME}"
    else
        echo "!! External storage path not found: ${EXTERNAL_COPY_DIR}"
    fi
fi

echo ""
echo "=== Backup complete ==="
