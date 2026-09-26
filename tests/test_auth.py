from httpx import AsyncClient


async def test_register_student(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@test.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Student"
    assert data["email"] == "student@test.com"
    assert data["role"] == "student"
    assert data["is_active"] is True


async def test_duplicate_registration(client: AsyncClient):
    payload = {
        "name": "Test Student",
        "email": "student@test.com",
        "password": "password123",
    }

    first = await client.post(
        "/auth/register",
        json=payload,
    )

    assert first.status_code == 201

    second = await client.post(
        "/auth/register",
        json=payload,
    )

    assert second.status_code == 400


async def test_login(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@test.com",
            "password": "password123",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@test.com",
            "password": "password123",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


async def test_me(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": "student@test.com",
            "password": "password123",
        },
    )

    login = await client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": "password123",
        },
    )

    token = login.json()["access_token"]

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "student@test.com"
    assert data["role"] == "student"


async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get("/auth/me")

    assert response.status_code == 401