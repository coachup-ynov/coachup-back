import enum
import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Visibility(enum.StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class Level(enum.StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


def _str_enum(enum_cls: type[enum.StrEnum]) -> Enum:
    """Stocke l'enum en VARCHAR (valeurs en minuscules) plutôt qu'en type ENUM Postgres."""
    return Enum(
        enum_cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    pseudonym: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    terms_version: Mapped[str] = mapped_column(String(20))
    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Profil, rempli pendant l'onboarding
    onboarding_completed: Mapped[bool] = mapped_column(default=False)
    sport: Mapped[str | None] = mapped_column(String(50))
    birth_date: Mapped[date | None] = mapped_column(Date)
    visibility: Mapped[Visibility] = mapped_column(_str_enum(Visibility), default=Visibility.PUBLIC)
    goals: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    level: Mapped[Level | None] = mapped_column(_str_enum(Level))

    sessions: Mapped[list["UserSession"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
