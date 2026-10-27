import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, generate_refresh_token, hash_token
from app.models.session import UserSession
from app.models.user import User
from app.schemas.auth import TokenResponse


def _issue_tokens(session: UserSession, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(session.user_id, session.id),
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def open_session(db: AsyncSession, user: User, user_agent: str | None) -> TokenResponse:
    refresh_token = generate_refresh_token()
    session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        user_agent=user_agent[:255] if user_agent else None,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()
    return _issue_tokens(session, refresh_token)


async def rotate_session(db: AsyncSession, refresh_token: str) -> TokenResponse | None:
    """Échange un refresh token valide contre une nouvelle paire de tokens."""
    now = datetime.now(UTC)
    session = await db.scalar(
        select(UserSession)
        .join(User)
        .where(
            UserSession.refresh_token_hash == hash_token(refresh_token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            User.is_active.is_(True),
        )
    )
    if session is None:
        return None
    new_refresh_token = generate_refresh_token()
    session.refresh_token_hash = hash_token(new_refresh_token)
    session.last_used_at = now
    await db.commit()
    return _issue_tokens(session, new_refresh_token)


async def revoke_sessions(
    db: AsyncSession, user_id: uuid.UUID, *, except_id: uuid.UUID | None = None
) -> None:
    query = update(UserSession).where(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    if except_id is not None:
        query = query.where(UserSession.id != except_id)
    await db.execute(query.values(revoked_at=datetime.now(UTC)))
