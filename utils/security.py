from passlib.context import CryptContext
import secrets
import os
from cryptography.fernet import Fernet
import base64
from typing import Optional

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

import logging

logger = logging.getLogger(__name__)

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
ALLOW_TEMP_ENCRYPTION = os.getenv("ALLOW_TEMP_ENCRYPTION", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "local")

if not ENCRYPTION_KEY:
    if APP_ENV == "local" or ALLOW_TEMP_ENCRYPTION:
        logger.warning("ENCRYPTION_KEY is not set. Using a generated temporary key. Data encrypted with this key will be UNRECOVERABLE across restarts.")
        ENCRYPTION_KEY = Fernet.generate_key().decode("utf-8")
    else:
        raise RuntimeError("CRITICAL: ENCRYPTION_KEY is missing. Temporary keys are disabled in non-local environments. Set ALLOW_TEMP_ENCRYPTION=true to override (NOT RECOMMENDED).")

if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode("utf-8")
_fernet = Fernet(ENCRYPTION_KEY)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)

def generate_secure_token() -> str:
    """Generate a secure urlsafe token for emails/resets."""
    return secrets.token_urlsafe(32)

def encrypt_string(plain_text: Optional[str]) -> Optional[str]:
    """Encrypt a string using symmetric encryption (Fernet)."""
    if plain_text is None:
        return None
    return _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_string(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt a string using symmetric encryption (Fernet).
    
    Raises:
        cryptography.fernet.InvalidToken: If cipher_text is invalid or tampered.
    """
    if cipher_text is None:
        return None
    return _fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
