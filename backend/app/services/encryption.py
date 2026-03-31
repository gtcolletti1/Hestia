"""
Encryption service for sensitive tokens (OAuth access/refresh tokens).

Uses Fernet symmetric encryption from the `cryptography` package.
The encryption key is derived from the application's SECRET_KEY so there
is a single secret to manage.

Usage example (encrypting OAuthCredential fields before persisting):

    from app.services.encryption import encrypt_token, decrypt_token

    # Encrypt before saving to the database
    credential.access_token  = encrypt_token(raw_access_token,  settings.SECRET_KEY)
    credential.refresh_token = encrypt_token(raw_refresh_token, settings.SECRET_KEY)
    db.commit()

    # Decrypt when reading back
    access_token  = decrypt_token(credential.access_token,  settings.SECRET_KEY)
    refresh_token = decrypt_token(credential.refresh_token, settings.SECRET_KEY)

Dependencies:
    pip install cryptography
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


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
