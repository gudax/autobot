"""
Encryption and hashing utilities
"""

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.config.settings import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token

    Args:
        token: JWT token to decode

    Returns:
        Decoded token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data (e.g., API tokens, passwords)
    Uses Fernet symmetric encryption

    Args:
        data: Data to encrypt

    Returns:
        Encrypted data as base64 string
    """
    from cryptography.fernet import Fernet
    import base64

    # Get encryption key from settings
    # In production, this should be loaded from secure environment variable
    encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)

    if not encryption_key:
        # Fallback to base64 for backwards compatibility
        # WARNING: This is NOT secure!
        import warnings
        warnings.warn("ENCRYPTION_KEY not set, using insecure base64 encoding!")
        return base64.b64encode(data.encode()).decode()

    # Ensure key is properly formatted
    if isinstance(encryption_key, str):
        encryption_key = encryption_key.encode()

    try:
        # Create Fernet cipher
        cipher = Fernet(encryption_key)

        # Encrypt data
        encrypted = cipher.encrypt(data.encode())

        # Return as base64 string for storage
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        # Log error and fallback to base64
        import logging
        logging.error(f"Encryption failed: {e}, falling back to base64")
        return base64.b64encode(data.encode()).decode()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data
    Uses Fernet symmetric encryption

    Args:
        encrypted_data: Encrypted data as base64 string

    Returns:
        Decrypted data
    """
    from cryptography.fernet import Fernet
    import base64

    # Get encryption key from settings
    encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)

    if not encryption_key:
        # Fallback to base64 for backwards compatibility
        try:
            return base64.b64decode(encrypted_data.encode()).decode()
        except Exception:
            # Already decoded or invalid
            return encrypted_data

    # Ensure key is properly formatted
    if isinstance(encryption_key, str):
        encryption_key = encryption_key.encode()

    try:
        # Create Fernet cipher
        cipher = Fernet(encryption_key)

        # Decode from base64 storage format
        encrypted_bytes = base64.b64decode(encrypted_data.encode())

        # Decrypt data
        decrypted = cipher.decrypt(encrypted_bytes)

        return decrypted.decode()
    except Exception as e:
        # Try base64 decoding as fallback (for old data)
        import logging
        logging.warning(f"Fernet decryption failed: {e}, trying base64 fallback")
        try:
            return base64.b64decode(encrypted_data.encode()).decode()
        except Exception:
            # Return as-is if all else fails
            return encrypted_data


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key

    Returns:
        Base64-encoded encryption key
    """
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()
