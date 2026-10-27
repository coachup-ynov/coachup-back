from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Email, Password, Pseudonym


class RegisterRequest(BaseModel):
    email: Email
    pseudonym: Pseudonym
    password: Password
    accept_terms: bool


class LoginRequest(BaseModel):
    email: Email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # durée de vie de l'access token, en secondes


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenRequest(BaseModel):
    token: str


class EmailRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Password


class TermsResponse(BaseModel):
    version: str
