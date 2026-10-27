from fastapi import HTTPException, status


class AppError(HTTPException):
    """Erreur métier renvoyée au front sous la forme {"detail": {"code", "message"}}."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def email_already_exists() -> AppError:
    return AppError(
        status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "Un compte existe déjà avec cet email."
    )


def pseudonym_already_exists() -> AppError:
    return AppError(
        status.HTTP_409_CONFLICT, "PSEUDONYM_ALREADY_EXISTS", "Ce pseudonyme est déjà utilisé."
    )


def terms_not_accepted() -> AppError:
    return AppError(
        status.HTTP_400_BAD_REQUEST,
        "TERMS_NOT_ACCEPTED",
        "Les conditions d'utilisation doivent être acceptées.",
    )


def invalid_credentials() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email ou mot de passe incorrect."
    )


def email_not_verified() -> AppError:
    return AppError(
        status.HTTP_403_FORBIDDEN,
        "EMAIL_NOT_VERIFIED",
        "L'adresse email doit être vérifiée avant de se connecter.",
    )


def account_disabled() -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, "ACCOUNT_DISABLED", "Ce compte est désactivé.")


def not_authenticated() -> AppError:
    error = AppError(status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED", "Authentification requise.")
    error.headers = {"WWW-Authenticate": "Bearer"}
    return error


def invalid_token() -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, "INVALID_TOKEN", "Lien invalide ou expiré.")


def invalid_refresh_token() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED, "INVALID_REFRESH_TOKEN", "Session expirée ou révoquée."
    )


def session_not_found() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "SESSION_NOT_FOUND", "Session introuvable.")
