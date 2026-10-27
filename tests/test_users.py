from datetime import date

from httpx import AsyncClient

from tests.conftest import Outbox, login, register

API = "/api/v1/users/me"

ONBOARDING = {
    "sport": "Course à pied",
    "birth_date": "2000-05-12",
    "visibility": "private",
    "goals": ["Courir un semi-marathon", "Perdre du poids"],
    "level": "intermediate",
}


async def test_read_me(client: AsyncClient, verified_user: dict) -> None:
    response = await client.get(API, headers=verified_user["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_onboarding(client: AsyncClient, verified_user: dict) -> None:
    response = await client.put(
        f"{API}/onboarding", json=ONBOARDING, headers=verified_user["headers"]
    )
    assert response.status_code == 200
    user = response.json()
    assert user["onboarding_completed"] is True
    assert user["level"] == "intermediate"
    assert user["visibility"] == "private"
    assert user["goals"] == ONBOARDING["goals"]
    assert user["age"] >= 26


async def test_onboarding_requires_all_fields(client: AsyncClient, verified_user: dict) -> None:
    response = await client.put(
        f"{API}/onboarding", json={"sport": "Tennis"}, headers=verified_user["headers"]
    )
    assert response.status_code == 422


async def test_onboarding_rejects_too_young(client: AsyncClient, verified_user: dict) -> None:
    birth_date = date.today().replace(year=date.today().year - 10).isoformat()
    response = await client.put(
        f"{API}/onboarding",
        json=ONBOARDING | {"birth_date": birth_date},
        headers=verified_user["headers"],
    )
    assert response.status_code == 422


async def test_onboarding_rejects_unknown_level(client: AsyncClient, verified_user: dict) -> None:
    response = await client.put(
        f"{API}/onboarding", json=ONBOARDING | {"level": "dieu"}, headers=verified_user["headers"]
    )
    assert response.status_code == 422


async def test_update_profile(client: AsyncClient, verified_user: dict) -> None:
    response = await client.patch(
        API,
        json={"pseudonym": "alice_runner", "level": "advanced"},
        headers=verified_user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["pseudonym"] == "alice_runner"
    assert response.json()["level"] == "advanced"


async def test_update_rejects_null_pseudonym(client: AsyncClient, verified_user: dict) -> None:
    response = await client.patch(API, json={"pseudonym": None}, headers=verified_user["headers"])
    assert response.status_code == 422


async def test_update_rejects_taken_pseudonym(client: AsyncClient, verified_user: dict) -> None:
    await register(client, email="bob@example.com", pseudonym="bob")
    response = await client.patch(API, json={"pseudonym": "bob"}, headers=verified_user["headers"])
    assert response.status_code == 409


async def test_change_email_requires_new_verification(
    client: AsyncClient, verified_user: dict, outbox: Outbox
) -> None:
    response = await client.patch(
        API, json={"email": "alice2@example.com"}, headers=verified_user["headers"]
    )
    assert response.status_code == 200
    assert response.json()["is_verified"] is False

    token = outbox.last_token("alice2@example.com")
    assert (
        await client.post("/api/v1/auth/verify-email", json={"token": token})
    ).status_code == 200
    assert (await login(client, email="alice2@example.com")).status_code == 200


async def test_old_verification_link_invalid_after_email_change(
    client: AsyncClient, outbox: Outbox
) -> None:
    await register(client)
    old_token = outbox.last_token("alice@example.com")
    await client.post("/api/v1/auth/verify-email", json={"token": old_token})
    headers = {"Authorization": f"Bearer {(await login(client)).json()['access_token']}"}
    await client.patch(API, json={"email": "alice2@example.com"}, headers=headers)

    response = await client.post("/api/v1/auth/verify-email", json={"token": old_token})
    assert response.status_code == 400


# --- Sessions ---


async def test_list_and_revoke_sessions(client: AsyncClient, verified_user: dict) -> None:
    other = (await login(client)).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    sessions = (await client.get(f"{API}/sessions", headers=verified_user["headers"])).json()
    assert len(sessions) == 2
    assert sum(s["current"] for s in sessions) == 1

    other_id = next(s["id"] for s in sessions if not s["current"])
    response = await client.delete(f"{API}/sessions/{other_id}", headers=verified_user["headers"])
    assert response.status_code == 204
    assert (await client.get(API, headers=other_headers)).status_code == 401
    assert (await client.get(API, headers=verified_user["headers"])).status_code == 200


async def test_revoke_other_sessions_keeps_current(
    client: AsyncClient, verified_user: dict
) -> None:
    other = (await login(client)).json()
    response = await client.delete(f"{API}/sessions", headers=verified_user["headers"])
    assert response.status_code == 204
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert (await client.get(API, headers=other_headers)).status_code == 401
    assert (await client.get(API, headers=verified_user["headers"])).status_code == 200


async def test_cannot_revoke_someone_else_session(
    client: AsyncClient, verified_user: dict, outbox: Outbox
) -> None:
    sessions = (await client.get(f"{API}/sessions", headers=verified_user["headers"])).json()
    await register(client, email="bob@example.com", pseudonym="bob")
    token = outbox.last_token("bob@example.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    bob = (await login(client, email="bob@example.com")).json()
    bob_headers = {"Authorization": f"Bearer {bob['access_token']}"}

    response = await client.delete(f"{API}/sessions/{sessions[0]['id']}", headers=bob_headers)
    assert response.status_code == 404
    assert (await client.get(API, headers=verified_user["headers"])).status_code == 200
