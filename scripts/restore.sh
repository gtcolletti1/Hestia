#!/usr/bin/env bash
# =============================================================================
# Family Hub — Database Restore
# Restores a PostgreSQL database from a gzipped backup file.
# =============================================================================
set -euo pipefail

# --- Usage ---
usage() {
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Restores the Family Hub database from a gzipped SQL dump."
    echo ""
    echo "Environment variables (or .env file):"
    echo "  POSTGRES_HOST      default: localhost"
    echo "  POSTGRES_PORT      default: 5432"
    echo "  POSTGRES_DB        default: familyhub"
    echo "  POSTGRES_USER      default: familyhub"
    echo "  POSTGRES_PASSWORD"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

BACKUP_FILE="$1"

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "Error: File not found: ${BACKUP_FILE}"
    exit 1
fi

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "${ENV_FILE}" ]]; then
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

echo "=== Family Hub Database Restore ==="
echo "Host:     ${PGHOST}:${PGPORT}"
echo "Database: ${PGDATABASE}"
echo "File:     ${BACKUP_FILE}"
echo ""

# --- Confirmation ---
read -rp "⚠️  This will DROP and recreate the '${PGDATABASE}' database. Continue? [y/N] " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo ">> Dropping existing database..."
dropdb --if-exists "${PGDATABASE}" 2>/dev/null || true

echo ">> Creating fresh database..."
createdb "${PGDATABASE}"

echo ">> Restoring from backup..."
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | psql --quiet --single-transaction "${PGDATABASE}"
else
    psql --quiet --single-transaction "${PGDATABASE}" < "${BACKUP_FILE}"
fi

echo ""
echo "=== Restore complete ==="
echo "Database '${PGDATABASE}' has been restored from ${BACKUP_FILE}"
