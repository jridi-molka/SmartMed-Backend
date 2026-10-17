USER = {"name": "Sarra", "email": "sarra@mail.com", "password": "123456"}


def register(client, user=USER):
    return client.post("/auth/register", json=user)


def login(client, email=USER["email"], password=USER["password"]):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(client):
    register(client)
    token = login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- register ----------

def test_register_success(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "sarra@mail.com"
    assert body["role"] == "Patient"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email(client):
    register(client)
    r = register(client)
    assert r.status_code == 409


def test_register_email_is_case_insensitive(client):
    register(client)
    r = register(client, {**USER, "email": "SARRA@mail.com"})
    assert r.status_code == 409


def test_register_invalid_email(client):
    r = register(client, {**USER, "email": "abc"})
    assert r.status_code == 422


def test_register_short_password(client):
    r = register(client, {**USER, "password": "12"})
    assert r.status_code == 422


def test_register_cannot_choose_role(client):
    r = register(client, {**USER, "role": "Admin"})
    assert r.status_code == 201
    assert r.json()["role"] == "Patient"


# ---------- login ----------

def test_login_success(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    register(client)
    r = login(client, password="faux")
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid credentials"}


def test_login_unknown_email(client):
    r = login(client, email="inconnu@mail.com")
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid credentials"}


# ---------- routes protégées ----------

def test_me_requires_token(client):
    r = client.get("/users/me")
    assert r.status_code in (401, 403)


def test_me_with_invalid_token(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401


def test_me_success(client):
    r = client.get("/users/me", headers=auth_header(client))
    assert r.status_code == 200
    assert r.json()["email"] == "sarra@mail.com"


def test_update_name(client):
    headers = auth_header(client)
    r = client.put("/users/me", json={"name": "Sarra Ben Ali"}, headers=headers)
    assert r.status_code == 200
    assert client.get("/users/me", headers=headers).json()["name"] == "Sarra Ben Ali"


def test_update_password(client):
    headers = auth_header(client)
    client.put("/users/me", json={"password": "nouveau123"}, headers=headers)
    assert login(client, password="123456").status_code == 401
    assert login(client, password="nouveau123").status_code == 200


def test_update_cannot_change_role(client):
    headers = auth_header(client)
    r = client.put("/users/me", json={"role": "Admin"}, headers=headers)
    assert r.json()["role"] == "Patient"


def test_logout(client):
    r = client.post("/auth/logout", headers=auth_header(client))
    assert r.status_code == 200