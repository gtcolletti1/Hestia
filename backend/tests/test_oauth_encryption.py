"""Tests for OAuth token encryption at rest.

Covers the `EncryptedString` SQLAlchemy TypeDecorator applied to
`OAuthCredential.access_token` and `refresh_token`:

* Values written via the ORM are stored as Fernet ciphertext on disk.
* Values read via the ORM come back as plaintext.
* Legacy plaintext rows can still be read (graceful fallback).
* `encrypt_token` / `decrypt_token` round-trip works.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import OAuthCredential, OAuthProvider
from app.models.user import Household
from app.services.encryption import (
    decrypt_token,
    encrypt_token,
)

pytestmark = pytest.mark.asyncio


async def test_encrypt_decrypt_roundtrip() -> None:
    key = "test-secret-key"
    plaintext = "ya29.A0ARrdaM-fakegoogletoken"
    ciphertext = encrypt_token(plaintext, key)

    assert ciphertext != plaintext
    assert ciphertext.startswith("gAAAAA"), "Fernet tokens start with gAAAAA"
    assert decrypt_token(ciphertext, key) == plaintext


async def test_orm_writes_ciphertext_and_reads_plaintext(
    db_session: AsyncSession, sample_household: Household
) -> None:
    raw_access = "access-token-plaintext-12345"
    raw_refresh = "refresh-token-plaintext-67890"

    cred = OAuthCredential(
        household_id=sample_household.id,
        provider=OAuthProvider.google,
        access_token=raw_access,
        refresh_token=raw_refresh,
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        scopes="https://www.googleapis.com/auth/calendar",
    )
    db_session.add(cred)
    await db_session.flush()
    cred_id = cred.id

    # Raw row should be ciphertext (bypass the ORM)
    row = (
        await db_session.execute(
            text("SELECT access_token, refresh_token FROM oauth_credentials")
        )
    ).one()
    raw_access_db, raw_refresh_db = row
    assert raw_access_db != raw_access
    assert raw_access_db.startswith("gAAAAA")
    assert raw_refresh_db != raw_refresh
    assert raw_refresh_db.startswith("gAAAAA")

    # Round-trip via ORM returns plaintext
    db_session.expire_all()
    fetched = await db_session.get(OAuthCredential, cred_id)
    assert fetched is not None
    assert fetched.access_token == raw_access
    assert fetched.refresh_token == raw_refresh


async def test_legacy_plaintext_is_returned_unchanged(
    db_session: AsyncSession, sample_household: Household
) -> None:
    """Pre-existing plaintext rows should still be readable via the ORM."""
    legacy_access = "legacy-plaintext-access-token"
    legacy_refresh = "legacy-plaintext-refresh-token"
    legacy_id = "0000000000004000800000000000abcd"

    # Insert directly with raw SQL so the TypeDecorator's bind step is skipped
    await db_session.execute(
        text(
            "INSERT INTO oauth_credentials "
            "(id, household_id, provider, access_token, refresh_token, "
            " token_expiry, scopes, created_at, updated_at) "
            "VALUES (:id, :hid, :prov, :a, :r, :exp, :s, :now, :now)"
        ),
        {
            "id": legacy_id,
            "hid": sample_household.id.hex,
            "prov": OAuthProvider.google.value,
            "a": legacy_access,
            "r": legacy_refresh,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "s": "scope",
            "now": datetime.now(timezone.utc),
        },
    )
    await db_session.flush()

    import uuid as _uuid
    fetched = await db_session.get(OAuthCredential, _uuid.UUID(legacy_id))
    assert fetched is not None
    # Plaintext returned unchanged (graceful fallback)
    assert fetched.access_token == legacy_access
    assert fetched.refresh_token == legacy_refresh


async def test_re_save_re_encrypts_legacy_row(
    db_session: AsyncSession, sample_household: Household
) -> None:
    """Re-saving a legacy plaintext row should encrypt it on disk."""
    legacy_id = "0000000000004000800000000000beef"
    await db_session.execute(
        text(
            "INSERT INTO oauth_credentials "
            "(id, household_id, provider, access_token, refresh_token, "
            " token_expiry, scopes, created_at, updated_at) "
            "VALUES (:id, :hid, :prov, :a, :r, :exp, :s, :now, :now)"
        ),
        {
            "id": legacy_id,
            "hid": sample_household.id.hex,
            "prov": OAuthProvider.microsoft.value,
            "a": "old-plain",
            "r": "old-plain-refresh",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "s": "scope",
            "now": datetime.now(timezone.utc),
        },
    )
    await db_session.flush()

    import uuid as _uuid
    fetched = await db_session.get(OAuthCredential, _uuid.UUID(legacy_id))
    assert fetched is not None

    # Mutate (simulating a token refresh) and flush
    fetched.access_token = "new-fresh-access"
    await db_session.flush()

    row = (
        await db_session.execute(
            text(
                "SELECT access_token FROM oauth_credentials WHERE id = :id"
            ),
            {"id": legacy_id},
        )
    ).one()
    assert row[0].startswith("gAAAAA")
    assert row[0] != "new-fresh-access"
