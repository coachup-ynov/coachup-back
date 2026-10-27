from httpx import AsyncClient

from tests.conftest import PASSWORD, Outbox, login, register

API = "/api/v1/auth"


def error_code(response) -> str:
    return response.json()["detail"]["code"]


# --- Inscription ---


async def test_register_creates_unverified_user_and_sends_email(
    client: AsyncClient, outbox: Outbox
) -> None:
    user = await register(client, email="Alice@Example.com", pseudonym="alice")
    assert user["email"] == "alice@example.com"
    assert user["is_verified"] is False
    assert user["onboarding_completed"] is False
    assert "hashed_password" not in user
    assert outbox[0][0] == "alice@example.com"


async def test_register_rejects_existing_email(client: AsyncClient) -> None:
    await register(client, pseudonym="alice")
    response = await client.post(
        f"{API}/register",
        json={
            "email": "ALICE@example.com",
            "pseudonym": "autre",
            "password": PASSWORD,
            "accept_terms": True,
        },
    )
    assert response.status_code == 409
    assert error_code(response) == "EMAIL_ALREADY_EXISTS"


async def test_register_rejects_existing_pseudonym(client: AsyncClient) -> None:
    await register(client, email="alice@example.com", pseudonym="alice")
    response = await client.post(
        f"{API}/register",
        json={
            "email": "bob@example.com",
            "pseudonym": "alice",
            "password": PASSWORD,
            "accept_terms": True,
        },
    )
    assert response.status_code == 409
    assert error_code(response) == "PSEUDONYM_ALREADY_EXISTS"


async def test_register_requires_terms(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/register",
        json={
            "email": "a@example.com",
            "pseudonym": "alice",
            "password": PASSWORD,
            "accept_terms": False,
        },
    )
    assert response.status_code == 400
    assert error_code(response) == "TERMS_NOT_ACCEPTED"


async def test_register_validates_input(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/register",
        json={"email": "pas-un-email", "pseudonym": "a", "password": "court", "accept_terms": True},
    )
    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert fields == {"email", "pseudonym", "password"}


async def test_terms_version(client: AsyncClient) -> None:
    response = await client.get(f"{API}/terms")
    assert response.status_code == 200
    assert response.json()["version"]


# --- Vérification de l'email ---


async def test_verify_email(client: AsyncClient, outbox: Outbox) -> None:
    await register(client)
    token = outbox.last_token("alice@example.com")
    response = await client.post(f"{API}/verify-email", json={"token": token})
    assert response.status_code == 200
    assert (await login(client)).status_code == 200


async def test_verify_email_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post(f"{API}/verify-email", json={"token": "faux"})
    assert response.status_code == 400
    assert error_code(response) == "INVALID_TOKEN"


async def test_resend_verification(client: AsyncClient, outbox: Outbox) -> None:
    await register(client)
    response = await client.post(f"{API}/resend-verification", json={"email": "alice@example.com"})
    assert response.status_code == 202
    assert len(outbox) == 2


async def test_resend_verification_unknown_email_is_silent(
    client: AsyncClient, outbox: Outbox
) -> None:
    response = await client.post(f"{API}/resend-verification", json={"email": "x@example.com"})
    assert response.status_code == 202
    assert outbox == []


# --- Connexion ---


async def test_login_requires_verified_email(client: AsyncClient) -> None:
    await register(client)
    response = await login(client)
    assert response.status_code == 403
    assert error_code(response) == "EMAIL_NOT_VERIFIED"


async def test_login_wrong_password(client: AsyncClient, verified_user: dict) -> None:
    response = await login(client, password="mauvais-mdp")
    assert response.status_code == 401
    assert error_code(response) == "INVALID_CREDENTIALS"


async def test_login_unknown_email(client: AsyncClient) -> None:
    response = await login(client, email="inconnu@example.com")
    assert response.status_code == 401
    assert error_code(response) == "INVALID_CREDENTIALS"


async def test_login_returns_tokens(verified_user: dict) -> None:
    assert verified_user["access_token"]
    assert verified_user["refresh_token"]
    assert verified_user["token_type"] == "bearer"


async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert error_code(response) == "NOT_AUTHENTICATED"


# --- Refresh et déconnexion ---


async def test_refresh_rotates_token(client: AsyncClient, verified_user: dict) -> None:
    old = verified_user["refresh_token"]
    response = await client.post(f"{API}/refresh", json={"refresh_token": old})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != old
    # L'ancien refresh token n'est plus utilisable
    response = await client.post(f"{API}/refresh", json={"refresh_token": old})
    assert response.status_code == 401


async def test_logout_revokes_session(client: AsyncClient, verified_user: dict) -> None:
    headers = verified_user["headers"]
    assert (await client.post(f"{API}/logout", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401
    response = await client.post(
        f"{API}/refresh", json={"refresh_token": verified_user["refresh_token"]}
    )
    assert response.status_code == 401


# --- Mot de passe oublié ---


async def test_reset_password(client: AsyncClient, verified_user: dict, outbox: Outbox) -> None:
    response = await client.post(f"{API}/forgot-password", json={"email": "alice@example.com"})
    assert response.status_code == 202
    token = outbox.last_token("alice@example.com")

    response = await client.post(
        f"{API}/reset-password", json={"token": token, "new_password": "nouveau-mdp-42"}
    )
    assert response.status_code == 200
    # Toutes les sessions sont révoquées
    assert (
        await client.get("/api/v1/users/me", headers=verified_user["headers"])
    ).status_code == 401
    assert (await login(client)).status_code == 401
    assert (await login(client, password="nouveau-mdp-42")).status_code == 200

    # Le lien ne fonctionne qu'une fois
    response = await client.post(
        f"{API}/reset-password", json={"token": token, "new_password": "encore-un-autre"}
    )
    assert response.status_code == 400


async def test_forgot_password_unknown_email_is_silent(client: AsyncClient, outbox: Outbox) -> None:
    response = await client.post(f"{API}/forgot-password", json={"email": "x@example.com"})
    assert response.status_code == 202
    assert outbox == []
