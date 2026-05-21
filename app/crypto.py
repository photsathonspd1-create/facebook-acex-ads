"""
Simple encryption utilities for sensitive data (e.g. Facebook tokens).
Uses Fernet symmetric encryption from the `cryptography` package.

Key is derived from ENCRYPTION_KEY env var (or falls back to SECRET_KEY).
"""
import os
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Lazy-initialize Fernet instance."""
    global _fernet
    if _fernet is not None:
        return _fernet

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.warning("cryptography package not installed — token encryption disabled")
        return None

    raw_key = os.environ.get('ENCRYPTION_KEY', '') or os.environ.get('SECRET_KEY', '')
    if not raw_key:
        logger.warning("No ENCRYPTION_KEY or SECRET_KEY set — token encryption disabled")
        return None

    # Derive a valid Fernet key from arbitrary string
    derived = hashlib.sha256(raw_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    _fernet = Fernet(fernet_key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns base64 ciphertext."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Encryption is disabled (no ENCRYPTION_KEY or SECRET_KEY)")
    try:
        return f.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise ValueError("Encryption failed") from e


def decrypt(ciphertext: str) -> str:
    """Decrypt a string. Returns plaintext."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    if f is None:
        raise RuntimeError("Decryption is disabled (no ENCRYPTION_KEY or SECRET_KEY)")
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError("Decryption failed. Token might be corrupt or unencrypted.") from e
