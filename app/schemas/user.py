import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from app.models.user import Level, Visibility
from app.schemas.common import BirthDate, Email, Goals, Pseudonym, Sport, compute_age


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    pseudonym: str
    is_verified: bool
    onboarding_completed: bool
    sport: str | None
    birth_date: date | None
    visibility: Visibility
    goals: list[str]
    level: Level | None
    terms_version: str
    created_at: datetime

    @computed_field
    @property
    def age(self) -> int | None:
        return compute_age(self.birth_date) if self.birth_date else None


class OnboardingRequest(BaseModel):
    sport: Sport
    birth_date: BirthDate
    visibility: Visibility
    goals: Goals
    level: Level


class UserUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs envoyés sont modifiés."""

    pseudonym: Pseudonym | None = None
    email: Email | None = None
    sport: Sport | None = None
    birth_date: BirthDate | None = None
    visibility: Visibility | None = None
    goals: Goals | None = None
    level: Level | None = None

    @model_validator(mode="after")
    def check_required_not_null(self) -> Self:
        for field in ("pseudonym", "email", "visibility", "goals"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Le champ '{field}' ne peut pas être null.")
        return self


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool = False
