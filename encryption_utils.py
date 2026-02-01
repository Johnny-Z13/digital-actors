"""
Database Encryption Utilities

Provides encryption/decryption functionality for sensitive player data.
Uses Fernet (symmetric encryption) from the cryptography library.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption-related errors."""

    pass


class DecryptionError(Exception):
    """Exception raised when decryption fails."""

    pass


class EncryptionKeyError(Exception):
    """Exception raised when encryption key is missing or invalid."""

    pass


def generate_key() -> str:
    """Generate a new Fernet encryption key.

    Returns:
        str: Base64-encoded encryption key

    Example:
        >>> key = generate_key()
        >>> len(key) > 0
        True
    """
    key = Fernet.generate_key()
    return key.decode("utf-8")


def _get_fernet_instance(key: str | None) -> Fernet:
    """Get a Fernet instance with the provided key.

    Args:
        key: Base64-encoded encryption key

    Returns:
        Fernet: Configured Fernet instance

    Raises:
        EncryptionKeyError: If key is missing or invalid
    """
    if not key:
        raise EncryptionKeyError("Encryption key is required but not provided")

    try:
        # Ensure key is bytes
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        return Fernet(key_bytes)
    except Exception as e:
        logger.error("Failed to create Fernet instance: %s", e, exc_info=True)
        raise EncryptionKeyError(f"Invalid encryption key format: {e}") from e


def encrypt_data(data: str | dict | list | None, key: str | None) -> str | None:
    """Encrypt data using Fernet symmetric encryption.

    Args:
        data: Data to encrypt (string, dict, list, or None)
        key: Base64-encoded encryption key from environment variable

    Returns:
        str | None: Base64-encoded encrypted data, or None if data is None

    Raises:
        EncryptionKeyError: If key is missing or invalid
        EncryptionError: If encryption fails

    Example:
        >>> key = generate_key()
        >>> encrypted = encrypt_data("sensitive data", key)
        >>> encrypted is not None
        True
    """
    if data is None:
        return None

    if not key:
        raise EncryptionKeyError("Cannot encrypt data without encryption key")

    try:
        # Convert data to string if it's a dict or list
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data)
        else:
            data_str = str(data)

        # Get Fernet instance
        fernet = _get_fernet_instance(key)

        # Encrypt the data
        encrypted_bytes = fernet.encrypt(data_str.encode("utf-8"))

        # Return as base64 string
        return encrypted_bytes.decode("utf-8")

    except EncryptionKeyError:
        raise
    except Exception as e:
        logger.error("Failed to encrypt data: %s", e, exc_info=True)
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt_data(
    encrypted_data: str | None, key: str | None, return_type: type = str
) -> Any | None:
    """Decrypt data using Fernet symmetric encryption.

    Args:
        encrypted_data: Base64-encoded encrypted data
        key: Base64-encoded encryption key from environment variable
        return_type: Expected return type (str, dict, list, or int)

    Returns:
        Decrypted data in the requested type, or None if encrypted_data is None

    Raises:
        EncryptionKeyError: If key is missing or invalid
        DecryptionError: If decryption fails or data is corrupted

    Example:
        >>> key = generate_key()
        >>> encrypted = encrypt_data({"name": "Alice"}, key)
        >>> decrypted = decrypt_data(encrypted, key, dict)
        >>> decrypted["name"]
        'Alice'
    """
    if encrypted_data is None:
        return None

    if not key:
        raise EncryptionKeyError("Cannot decrypt data without encryption key")

    try:
        # Get Fernet instance
        fernet = _get_fernet_instance(key)

        # Decrypt the data
        decrypted_bytes = fernet.decrypt(encrypted_data.encode("utf-8"))
        decrypted_str = decrypted_bytes.decode("utf-8")

        # Convert to requested type
        if return_type == dict:
            return json.loads(decrypted_str)
        elif return_type == list:
            return json.loads(decrypted_str)
        elif return_type == int:
            return int(decrypted_str)
        else:
            return decrypted_str

    except InvalidToken as e:
        logger.error("Invalid encryption token - data may be corrupted or key is wrong: %s", e)
        raise DecryptionError(
            "Failed to decrypt data: invalid token (wrong key or corrupted data)"
        ) from e
    except EncryptionKeyError:
        raise
    except Exception as e:
        logger.error("Failed to decrypt data: %s", e, exc_info=True)
        raise DecryptionError(f"Decryption failed: {e}") from e


def rotate_key(old_key: str, new_key: str, encrypted_data: str) -> str:
    """Rotate encryption key by decrypting with old key and re-encrypting with new key.

    Args:
        old_key: Current encryption key
        new_key: New encryption key to use
        encrypted_data: Data encrypted with old key

    Returns:
        str: Data re-encrypted with new key

    Raises:
        EncryptionKeyError: If either key is missing or invalid
        DecryptionError: If decryption with old key fails
        EncryptionError: If encryption with new key fails

    Example:
        >>> old_key = generate_key()
        >>> new_key = generate_key()
        >>> encrypted = encrypt_data("secret", old_key)
        >>> re_encrypted = rotate_key(old_key, new_key, encrypted)
        >>> decrypt_data(re_encrypted, new_key)
        'secret'
    """
    if not old_key or not new_key:
        raise EncryptionKeyError("Both old and new encryption keys are required")

    # Decrypt with old key
    decrypted = decrypt_data(encrypted_data, old_key, str)

    # Re-encrypt with new key
    return encrypt_data(decrypted, new_key)


def is_encryption_enabled(key: str | None) -> bool:
    """Check if encryption is enabled (key is provided).

    Args:
        key: Encryption key from environment

    Returns:
        bool: True if encryption key is available and valid

    Example:
        >>> is_encryption_enabled(None)
        False
        >>> is_encryption_enabled("")
        False
        >>> key = generate_key()
        >>> is_encryption_enabled(key)
        True
    """
    if not key:
        return False

    try:
        _get_fernet_instance(key)
        return True
    except EncryptionKeyError:
        return False
