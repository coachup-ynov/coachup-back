import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select

from app.api.deps import CurrentSession, CurrentUser, SessionDep
from app.core import errors
from app.models.session import UserSession
from app.models.user import User
from app.schemas.user import OnboardingRequest, SessionRead, UserRead, UserUpdate
from app.services import auth as auth_service
from app.services.email import build_verification_email, send_email

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("")
async def update_me(
    body: UserUpdate, user: CurrentUser, db: SessionDep, background_tasks: BackgroundTasks
) -> UserRead:
    changes = body.model_dump(exclude_unset=True)

    if "pseudonym" in changes and changes["pseudonym"] != user.pseudonym:
        taken = await db.scalar(select(User.id).where(User.pseudonym == changes["pseudonym"]))
        if taken:
            raise errors.pseudonym_already_exists()

    email_changed = "email" in changes and changes["email"] != user.email
    if email_changed:
        if await db.scalar(select(User.id).where(User.email == changes["email"])):
            raise errors.email_already_exists()
        # La nouvelle adresse doit être vérifiée à son tour
        user.is_verified = False

    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)

    if email_changed:
        background_tasks.add_task(send_email, *build_verification_email(user))
    return UserRead.model_validate(user)


@router.put("/onboarding")
async def complete_onboarding(
    body: OnboardingRequest, user: CurrentUser, db: SessionDep
) -> UserRead:
    for field, value in body.model_dump().items():
        setattr(user, field, value)
    user.onboarding_completed = True
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.get("/sessions")
async def list_sessions(current: CurrentSession, db: SessionDep) -> list[SessionRead]:
    sessions = await db.scalars(
        select(UserSession)
        .where(
            UserSession.user_id == current.user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
        .order_by(UserSession.last_used_at.desc())
    )
    return [
        SessionRead.model_validate(s).model_copy(update={"current": s.id == current.id})
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: uuid.UUID, current: CurrentSession, db: SessionDep) -> None:
    session = await db.get(UserSession, session_id)
    if session is None or session.user_id != current.user_id or session.revoked_at:
        raise errors.session_not_found()
    session.revoked_at = datetime.now(UTC)
    await db.commit()


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_other_sessions(current: CurrentSession, db: SessionDep) -> None:
    """Déconnecte tous les autres appareils, en gardant la session courante."""
    await auth_service.revoke_sessions(db, current.user_id, except_id=current.id)
    await db.commit()
