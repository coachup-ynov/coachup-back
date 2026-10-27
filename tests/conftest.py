import os
import re
from collections.abc import AsyncIterator

# Base dédiée aux tests, pour ne jamais toucher à la base de dev
os.environ["ENVIRONMENT"] = "test"
os.environ["POSTGRES_DB"] = "coachup_test"
os.environ["SECRET_KEY"] = "test-secret-key-suffisamment-longue-pour-hs256"

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

PASSWORD = "motdepasse123"


async def _create_test_database() -> None:
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.POSTGRES_DB
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.POSTGRES_DB}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    await _create_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))


class Outbox(list):
    def last_token(self, to: str) -> str:
        for recipient, _subject, body in reversed(self):
            if recipient == to:
                return re.search(r"token=([\w.-]+)", body).group(1)
        raise AssertionError(f"Aucun email envoyé à {to}")


@pytest.fixture(autouse=True)
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """Remplace l'envoi SMTP : les emails sont capturés ici."""
    sent = Outbox()

    async def fake_send(to: str, subject: str, body: str) -> None:
        sent.append((to, subject, body))

    monkeypatch.setattr("app.api.v1.routes.auth.send_email", fake_send)
    monkeypatch.setattr("app.api.v1.routes.users.send_email", fake_send)
    return sent


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register(client: AsyncClient, email: str = "alice@example.com", **overrides) -> dict:
    body = {"email": email, "pseudonym": email.split("@")[0], "password": PASSWORD}
    response = await client.post(
        "/api/v1/auth/register", json=body | {"accept_terms": True} | overrides
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str = "alice@example.com", password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


@pytest.fixture
async def verified_user(client: AsyncClient, outbox: Outbox) -> dict:
    """Utilisateur inscrit, email vérifié et connecté. Contient ses tokens et un header d'auth."""
    user = await register(client)
    await client.post("/api/v1/auth/verify-email", json={"token": outbox.last_token(user["email"])})
    tokens = (await login(client)).json()
    return user | tokens | {"headers": {"Authorization": f"Bearer {tokens['access_token']}"}}
