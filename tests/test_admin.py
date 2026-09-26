from httpx import AsyncClient

from src.auth.models import User, UserRole
from src.auth.security import hash_password


async def create_user(db, *, name, email, password, role):
    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def login(client: AsyncClient, email: str, password: str):
    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


async def test_admin_can_create_professor(client, db):
    await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.post(
        "/admin/professors",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Professor",
            "email": "professor@test.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Professor"
    assert data["email"] == "professor@test.com"
    assert data["role"] == "professor"
    assert data["is_active"] is True


async def test_student_cannot_access_admin_users(client, db):
    await create_user(
        db,
        name="Test Student",
        email="student@test.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "student@test.com",
        "password123",
    )

    response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_professor_cannot_access_admin_users(client, db):
    await create_user(
        db,
        name="Test Professor",
        email="professor@test.com",
        password="password123",
        role=UserRole.PROFESSOR,
    )

    token = await login(
        client,
        "professor@test.com",
        "password123",
    )

    response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_unauthenticated_user_cannot_access_admin_users(client):
    response = await client.get("/admin/users")

    assert response.status_code == 401


async def test_admin_can_list_users(client, db):
    await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    await create_user(
        db,
        name="Test Student",
        email="student@test.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    users = response.json()

    assert len(users) == 2

    emails = {user["email"] for user in users}

    assert "admin@test.com" in emails
    assert "student@test.com" in emails


async def test_admin_cannot_delete_themselves(client, db):
    admin = await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.delete(
        f"/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


async def test_admin_can_delete_user(client, db):
    await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    student = await create_user(
        db,
        name="Test Student",
        email="student@test.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.delete(
        f"/admin/users/{student.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == student.id


async def test_admin_can_deactivate_user(client, db):
    await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    student = await create_user(
        db,
        name="Test Student",
        email="student@test.com",
        password="password123",
        role=UserRole.STUDENT,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.patch(
        f"/admin/users/{student.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == student.id
    assert data["is_active"] is False


async def test_admin_cannot_deactivate_themselves(client, db):
    admin = await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.patch(
        f"/admin/users/{admin.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 400


async def test_admin_cannot_deactivate_last_active_admin(client, db):
    admin = await create_user(
        db,
        name="Test Admin",
        email="admin@test.com",
        password="password123",
        role=UserRole.ADMIN,
    )

    token = await login(
        client,
        "admin@test.com",
        "password123",
    )

    response = await client.patch(
        f"/admin/users/{admin.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )

    assert response.status_code == 400