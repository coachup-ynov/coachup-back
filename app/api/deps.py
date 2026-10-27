import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import not_authenticated
from app.core.security import decode_token
from app.db.session import get_db
from app.models.session import UserSession
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_session(
    db: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserSession:
    if credentials is None:
        raise not_authenticated()
    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise not_authenticated()
    try:
        session_id = uuid.UUID(payload["sid"])
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise not_authenticated() from None

    # La session est vérifiée à chaque requête pour qu'une déconnexion soit immédiate
    session = await db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if session is None or not session.user.is_active:
        raise not_authenticated()
    return session


CurrentSession = Annotated[UserSession, Depends(get_current_session)]


async def get_current_user(session: CurrentSession) -> User:
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]
