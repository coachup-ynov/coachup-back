import logging
from datetime import timedelta
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.security import create_token, password_fingerprint
from app.models.user import User

logger = logging.getLogger(__name__)

Email = tuple[str, str, str]  # (destinataire, sujet, corps)


async def send_email(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        await aiosmtplib.send(message, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT)
    except aiosmtplib.SMTPException:
        logger.exception("Échec de l'envoi de l'email à %s", to)


def build_verification_email(user: User) -> Email:
    token = create_token(
        user.id,
        "email_verification",
        timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS),
        email=user.email,
    )
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    body = (
        f"Bonjour {user.pseudonym},\n\n"
        f"Confirme ton adresse email en cliquant sur ce lien :\n{link}\n\n"
        f"Ce lien expire dans {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} heures."
    )
    return user.email, "Confirme ton adresse email", body


def build_password_reset_email(user: User) -> Email:
    token = create_token(
        user.id,
        "password_reset",
        timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        pwd=password_fingerprint(user.hashed_password),
    )
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    body = (
        f"Bonjour {user.pseudonym},\n\n"
        f"Pour choisir un nouveau mot de passe, clique sur ce lien :\n{link}\n\n"
        f"Ce lien expire dans {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes. "
        "Si tu n'es pas à l'origine de cette demande, ignore cet email."
    )
    return user.email, "Réinitialisation de ton mot de passe", body
