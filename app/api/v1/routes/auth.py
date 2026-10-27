import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentSession, SessionDep
from app.core import errors
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TermsResponse,
    TokenRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services import auth as auth_service
from app.services.email import build_password_reset_email, build_verification_email, send_email

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_user_by_email(db: SessionDep, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def _get_user_by_token(db: SessionDep, payload: dict | None) -> User | None:
    if payload is None:
        return None
    try:
        return await db.get(User, uuid.UUID(payload["sub"]))
    except (KeyError, ValueError):
        return None


@router.get("/terms")
async def get_terms() -> TermsResponse:
    return TermsResponse(version=settings.TERMS_VERSION)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, db: SessionDep, background_tasks: BackgroundTasks
) -> UserRead:
    if not body.accept_terms:
        raise errors.terms_not_accepted()
    if await _get_user_by_email(db, body.email):
        raise errors.email_already_exists()
    if await db.scalar(select(User.id).where(User.pseudonym == body.pseudonym)):
        raise errors.pseudonym_already_exists()

    user = User(
        email=body.email,
        pseudonym=body.pseudonym,
        hashed_password=hash_password(body.password),
        terms_version=settings.TERMS_VERSION,
        terms_accepted_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Deux inscriptions simultanées avec le même email ou pseudonyme
        await db.rollback()
        raise errors.email_already_exists() from None
    await db.refresh(user)

    background_tasks.add_task(send_email, *build_verification_email(user))
    return UserRead.model_validate(user)


@router.post("/verify-email")
async def verify_email(body: TokenRequest, db: SessionDep) -> MessageResponse:
    payload = decode_token(body.token, "email_verification")
    user = await _get_user_by_token(db, payload)
    # Le token est lié à l'email : il devient invalide si l'email a changé entre-temps
    if user is None or payload.get("email") != user.email:
        raise errors.invalid_token()
    if not user.is_verified:
        user.is_verified = True
        await db.commit()
    return MessageResponse(message="Adresse email vérifiée.")


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    body: EmailRequest, db: SessionDep, background_tasks: BackgroundTasks
) -> MessageResponse:
    user = await _get_user_by_email(db, body.email)
    if user and not user.is_verified:
        background_tasks.add_task(send_email, *build_verification_email(user))
    return MessageResponse(message="Si un compte non vérifié existe, un email a été envoyé.")


@router.post("/login")
async def login(
    body: LoginRequest,
    db: SessionDep,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    user = await _get_user_by_email(db, body.email)
    if user is None:
        verify_password(body.password, DUMMY_PASSWORD_HASH)
        raise errors.invalid_credentials()
    if not verify_password(body.password, user.hashed_password):
        raise errors.invalid_credentials()
    if not user.is_active:
        raise errors.account_disabled()
    if not user.is_verified:
        raise errors.email_not_verified()
    return await auth_service.open_session(db, user, user_agent)


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: SessionDep) -> TokenResponse:
    tokens = await auth_service.rotate_session(db, body.refresh_token)
    if tokens is None:
        raise errors.invalid_refresh_token()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: CurrentSession, db: SessionDep) -> None:
    session.revoked_at = datetime.now(UTC)
    await db.commit()


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: EmailRequest, db: SessionDep, background_tasks: BackgroundTasks
) -> MessageResponse:
    user = await _get_user_by_email(db, body.email)
    if user and user.is_active:
        background_tasks.add_task(send_email, *build_password_reset_email(user))
    return MessageResponse(
        message="Si un compte existe, un email de réinitialisation a été envoyé."
    )


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: SessionDep) -> MessageResponse:
    payload = decode_token(body.token, "password_reset")
    user = await _get_user_by_token(db, payload)
    # L'empreinte change avec le mot de passe : le lien ne sert qu'une fois
    if user is None or payload.get("pwd") != password_fingerprint(user.hashed_password):
        raise errors.invalid_token()

    user.hashed_password = hash_password(body.new_password)
    # Le lien a été reçu par email : l'adresse est donc vérifiée
    user.is_verified = True
    await auth_service.revoke_sessions(db, user.id)
    await db.commit()
    return MessageResponse(message="Mot de passe modifié. Reconnecte-toi.")
