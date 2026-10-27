import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"

TokenPurpose = Literal["access", "email_verification", "password_reset"]

password_hash = PasswordHash.recommended()

# Hash factice pour garder un temps de réponse constant quand l'utilisateur n'existe pas
DUMMY_PASSWORD_HASH = password_hash.hash("dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_token(
    subject: uuid.UUID, purpose: TokenPurpose, expires_in: timedelta, **claims: Any
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(subject), "purpose": purpose, "iat": now, "exp": now + expires_in}
    return jwt.encode(payload | claims, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, purpose: TokenPurpose) -> dict[str, Any] | None:
    """Retourne le payload si le token est valide et a le bon usage, sinon None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    return create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        sid=str(session_id),
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_fingerprint(hashed_password: str) -> str:
    """Change dès que le mot de passe change : rend les liens de réinitialisation à usage unique."""
    return hash_token(hashed_password)[:16]
