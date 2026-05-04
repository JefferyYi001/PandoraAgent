"""API Key encryption utility using Fernet symmetric encryption."""

import os
from cryptography.fernet import Fernet


def generate_key() -> bytes:
    """Generate a new Fernet key."""
    return Fernet.generate_key()


def get_key() -> bytes:
    """Get encryption key from .env or generate new one."""
    key_str = os.getenv("ENCRYPTION_KEY")
    if not key_str:
        key = generate_key()
        os.environ["ENCRYPTION_KEY"] = key.decode()
        return key
    return key_str.encode()


def encrypt_token(token: str) -> str:
    """Encrypt an API key or token."""
    if not token:
        return ""
    f = Fernet(get_key())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt an encrypted API key or token."""
    if not encrypted:
        return ""
    f = Fernet(get_key())
    return f.decrypt(encrypted.encode()).decode()
