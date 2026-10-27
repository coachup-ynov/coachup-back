from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

MIN_AGE = 15
MAX_AGE = 120

Email = Annotated[EmailStr, AfterValidator(str.lower)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
Pseudonym = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=30, pattern=r"^[\w.-]+$"),
]
Sport = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Goal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Goals = Annotated[list[Goal], Field(max_length=10)]


def compute_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def _check_birth_date(value: date) -> date:
    if not MIN_AGE <= compute_age(value) <= MAX_AGE:
        raise ValueError(f"L'âge doit être compris entre {MIN_AGE} et {MAX_AGE} ans.")
    return value


BirthDate = Annotated[date, AfterValidator(_check_birth_date)]


class MessageResponse(BaseModel):
    message: str
