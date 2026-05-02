"""Encrypt existing OAuth credential tokens at rest.

Existing rows in ``oauth_credentials`` may have ``access_token`` /
``refresh_token`` stored as plaintext. The columns are now backed by the
``EncryptedString`` TypeDecorator, but pre-existing rows are not
automatically rewritten. This migration walks the table and rewrites any
plaintext token values as Fernet ciphertext using the current
``settings.SECRET_KEY``. Already-encrypted values are left alone.

The schema itself is unchanged (still ``TEXT``); this is data-only.

Revision ID: 7c4f9b1d3a22
Revises: 4a1c9b2d8e10
Create Date: 2026-05-02 11:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7c4f9b1d3a22"
down_revision: Union[str, None] = "4a1c9b2d8e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_already_encrypted(value: str, key: str) -> bool:
    from app.services.encryption import decrypt_token
    from cryptography.fernet import InvalidToken

    if not value or not value.startswith("gAAAAA"):
        return False
    try:
        decrypt_token(value, key)
        return True
    except InvalidToken:
        return False


def upgrade() -> None:
    from app.config import get_settings
    from app.services.encryption import encrypt_token

    key = get_settings().SECRET_KEY
    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT id, access_token, refresh_token FROM oauth_credentials"
        )
    ).fetchall()

    for row in rows:
        new_access = (
            row.access_token
            if _is_already_encrypted(row.access_token, key)
            else encrypt_token(row.access_token, key)
        )
        new_refresh = None
        if row.refresh_token is not None:
            new_refresh = (
                row.refresh_token
                if _is_already_encrypted(row.refresh_token, key)
                else encrypt_token(row.refresh_token, key)
            )

        bind.execute(
            sa.text(
                "UPDATE oauth_credentials "
                "SET access_token = :a, refresh_token = :r "
                "WHERE id = :id"
            ),
            {"a": new_access, "r": new_refresh, "id": row.id},
        )


def downgrade() -> None:
    """Decrypt tokens back to plaintext (best-effort)."""
    from app.config import get_settings
    from app.services.encryption import decrypt_token
    from cryptography.fernet import InvalidToken

    key = get_settings().SECRET_KEY
    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT id, access_token, refresh_token FROM oauth_credentials"
        )
    ).fetchall()

    for row in rows:
        try:
            new_access = decrypt_token(row.access_token, key)
        except InvalidToken:
            new_access = row.access_token

        new_refresh = None
        if row.refresh_token is not None:
            try:
                new_refresh = decrypt_token(row.refresh_token, key)
            except InvalidToken:
                new_refresh = row.refresh_token

        bind.execute(
            sa.text(
                "UPDATE oauth_credentials "
                "SET access_token = :a, refresh_token = :r "
                "WHERE id = :id"
            ),
            {"a": new_access, "r": new_refresh, "id": row.id},
        )
