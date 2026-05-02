"""
Encryption service for sensitive tokens (OAuth access/refresh tokens).

Uses Fernet symmetric encryption from the `cryptography` package.
The encryption key is derived from the application's SECRET_KEY so there
is a single secret to manage.

Two ways to use this module:

1. Direct functions ``encrypt_token`` / ``decrypt_token`` — explicit, takes
   the key as an argument.

2. ``EncryptedString`` SQLAlchemy ``TypeDecorator`` — recommended. Apply to
   model columns so reads/writes are automatically encrypted/decrypted.
   Reads fall back to returning the stored value unchanged when decryption
   fails, so pre-existing plaintext rows continue to work until migrated.

Dependencies:
    pip install cryptography
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


def _derive_key(secret: str) -> bytes:
    """
    Derive a 32-byte, URL-safe-base64-encoded key from an arbitrary secret
    string.  Fernet requires exactly 32 url-safe base64-encoded bytes.
    """
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plaintext: str, key: str) -> str:
    """
    Encrypt a plaintext string and return the ciphertext as a UTF-8 string.

    Args:
        plaintext: The value to encrypt (e.g. an OAuth access token).
        key:       The application secret key (e.g. settings.SECRET_KEY).

    Returns:
        A Fernet-encrypted, base64-encoded string safe for database storage.
    """
    fernet = Fernet(_derive_key(key))
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, key: str) -> str:
    """
    Decrypt a ciphertext string back to plaintext.

    Args:
        ciphertext: The encrypted value returned by ``encrypt_token``.
        key:        The same application secret key used for encryption.

    Returns:
        The original plaintext string.

    Raises:
        cryptography.fernet.InvalidToken: If the key is wrong or data is
            corrupted.
    """
    fernet = Fernet(_derive_key(key))
    return fernet.decrypt(ciphertext.encode()).decode()


def _looks_like_fernet(value: str) -> bool:
    """Heuristic: Fernet tokens start with 'gAAAAA' once base64-decoded the
    version byte is 0x80. We just check the urlsafe-base64 prefix here."""
    return isinstance(value, str) and value.startswith("gAAAAA")


class EncryptedString(TypeDecorator):
    """A SQLAlchemy column type that transparently encrypts strings at rest.

    Uses Fernet symmetric encryption keyed off ``settings.SECRET_KEY``.

    Behavior:
      * On write, the plaintext is encrypted before being persisted.
      * On read, the stored value is decrypted. If decryption fails (the
        value is plaintext from before this column was encrypted, or was
        encrypted with a different key), the raw stored value is returned
        unchanged and a warning is logged. This lets existing rows keep
        working until a migration re-encrypts them.

    The key is fetched lazily so changing ``SECRET_KEY`` at test time via
    settings overrides is honored.
    """

    impl = Text
    cache_ok = True

    @staticmethod
    def _key() -> str:
        # Lazy import to avoid a circular dependency with app.config at
        # import time, and to honor test-time settings overrides.
        from app.config import get_settings

        return get_settings().SECRET_KEY

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        # Avoid double-encrypting if a caller hands us an already-encrypted
        # value (e.g., copying a row).
        if _looks_like_fernet(value):
            try:
                # Validate it really is a token we can decrypt; if not,
                # treat as plaintext and encrypt.
                decrypt_token(value, self._key())
                return value
            except InvalidToken:
                pass
        return encrypt_token(value, self._key())

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return decrypt_token(value, self._key())
        except (InvalidToken, ValueError, TypeError):
            # Legacy plaintext or value encrypted with a different key.
            # Return as-is so the application keeps functioning; the next
            # write will re-encrypt with the current key.
            logger.warning(
                "EncryptedString: decrypt failed; returning value unchanged "
                "(likely legacy plaintext). Re-save to re-encrypt."
            )
            return value
