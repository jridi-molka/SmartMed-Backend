import pytest

from app.core.security import hash_password
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from tests.helpers import patient_header


def make_doctor(db, name, specialty="Généraliste", city="Tunis"):
    """Crée un médecin (compte + fiche) avec le nom, la spécialité et la ville voulus."""
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '.')}@mail.com",
        password_hash=hash_password("123456"),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    db.flush()
    doctor = Doctor(
        user_id=user.id,
        specialty=specialty,
        city=city,
        consultation_duration_min=20,
    )
    db.add(doctor)
    db.commit()
    return doctor


@pytest.fixture
def doctors(db):
    """4 médecins : par ordre alphabétique Amira, Karim, Salah, Salma."""
    return [
        make_doctor(db, "Dr Salma", "Cardiologue", "Tunis"),
        make_doctor(db, "Dr Salah", "Dentiste", "Sfax"),
        make_doctor(db, "Dr Karim", "Cardiologue", "Sfax"),
        make_doctor(db, "Dr Amira", "Pédiatre", "Tunis"),
    ]


def search(client, **params):
    return client.get("/doctors", params=params, headers=patient_header(client))


def names(response):
    return [d["name"] for d in response.json()["items"]]


def test_list_nominal(client, doctors):
    r = search(client)
    assert r.status_code == 200
    assert r.json()["total"] == 4
    assert names(r) == ["Dr Amira", "Dr Karim", "Dr Salah", "Dr Salma"]


def test_filter_specialty_ignores_case(client, doctors):
    r = search(client, specialty="cardiologue")
    assert r.json()["total"] == 2
    assert names(r) == ["Dr Karim", "Dr Salma"]


def test_filter_city(client, doctors):
    r = search(client, city="sfax")
    assert names(r) == ["Dr Karim", "Dr Salah"]


def test_search_name_partial(client, doctors):
    r = search(client, name="sal")
    assert names(r) == ["Dr Salah", "Dr Salma"]


def test_combined_filters(client, doctors):
    r = search(client, specialty="Cardiologue", city="Sfax")
    assert names(r) == ["Dr Karim"]
    assert r.json()["total"] == 1


def test_no_result_is_empty_list_not_error(client, doctors):
    r = search(client, name="zzz")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}


def test_sort_descending(client, doctors):
    r = search(client, sort="-name")
    assert names(r)[0] == "Dr Salma"


def test_pagination(client, doctors):
    page1 = search(client, limit=3, skip=0)
    page2 = search(client, limit=3, skip=3)
    assert len(page1.json()["items"]) == 3
    assert len(page2.json()["items"]) == 1
    assert page1.json()["total"] == 4  # le total ignore la pagination
    assert page2.json()["total"] == 4


def test_invalid_parameters(client, doctors):
    assert search(client, limit=500).status_code == 422
    assert search(client, limit=0).status_code == 422
    assert search(client, skip=-1).status_code == 422
    assert search(client, sort="age").status_code == 422


def test_response_hides_private_data(client, doctors):
    item = search(client).json()["items"][0]
    assert set(item) == {
        "id", "user_id", "name", "specialty", "bio",
        "address", "city", "consultation_duration_min",
    }


def test_doctors_requires_token(client, doctors):
    r = client.get("/doctors")
    assert r.status_code in (401, 403)


def test_specialties(client, doctors):
    r = client.get("/doctors/specialties", headers=patient_header(client))
    assert r.status_code == 200
    assert r.json() == ["Cardiologue", "Dentiste", "Pédiatre"]


def test_specialties_requires_token(client):
    r = client.get("/doctors/specialties")
    assert r.status_code in (401, 403)


def test_doctor_detail(client, doctors):
    doctor = doctors[0]  # Dr Salma
    r = client.get(f"/doctors/{doctor.id}", headers=patient_header(client))
    assert r.status_code == 200
    assert r.json()["name"] == "Dr Salma"
    assert r.json()["specialty"] == "Cardiologue"


def test_doctor_detail_unknown_id(client, doctors):
    r = client.get("/doctors/9999", headers=patient_header(client))
    assert r.status_code == 404


def test_doctor_detail_invalid_id(client, doctors):
    r = client.get("/doctors/abc", headers=patient_header(client))
    assert r.status_code == 422


def test_doctor_detail_requires_token(client, doctors):
    r = client.get(f"/doctors/{doctors[0].id}")
    assert r.status_code in (401, 403)    



# ---------- Profil du médecin connecté (D01, D02, D03) ----------

def make_doctor_account(db, email, name="Dr Nouveau"):
    """Un compte médecin SANS fiche (comme un médecin qui vient de s'inscrire)."""
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("123456"),
        role=UserRole.DOCTOR,
    )
    db.add(user)
    db.commit()
    return user


def login_header(client, email):
    token = client.post(
        "/auth/login", json={"email": email, "password": "123456"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


PROFILE = {
    "specialty": "Cardiologue",
    "bio": "10 ans d'expérience",
    "address": "12 rue X",
    "city": "Tunis",
    "consultation_duration_min": 25,
}


def test_create_profile_nominal(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    r = client.post("/doctors/me", json=PROFILE, headers=h)
    assert r.status_code == 201
    assert r.json()["name"] == "Dr Nouveau"
    assert r.json()["specialty"] == "Cardiologue"
    assert r.json()["consultation_duration_min"] == 25


def test_create_profile_defaults_and_trims_spaces(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    r = client.post("/doctors/me", json={"specialty": "  Dentiste "}, headers=h)
    assert r.status_code == 201
    assert r.json()["specialty"] == "Dentiste"
    assert r.json()["consultation_duration_min"] == 20


def test_create_profile_twice_is_409(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    assert client.post("/doctors/me", json=PROFILE, headers=h).status_code == 201
    assert client.post("/doctors/me", json=PROFILE, headers=h).status_code == 409


def test_create_profile_invalid_data_is_422(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    assert client.post("/doctors/me", json={}, headers=h).status_code == 422
    bad_duration = {**PROFILE, "consultation_duration_min": 3}
    assert client.post("/doctors/me", json=bad_duration, headers=h).status_code == 422
    short = {**PROFILE, "specialty": "A"}
    assert client.post("/doctors/me", json=short, headers=h).status_code == 422


def test_patient_cannot_use_doctor_profile_routes(client):
    h = patient_header(client)
    assert client.post("/doctors/me", json=PROFILE, headers=h).status_code == 403
    assert client.get("/doctors/me", headers=h).status_code == 403
    assert client.put("/doctors/me", json={"bio": "x"}, headers=h).status_code == 403


def test_profile_routes_require_token(client):
    assert client.post("/doctors/me", json=PROFILE).status_code in (401, 403)
    assert client.get("/doctors/me").status_code in (401, 403)
    assert client.put("/doctors/me", json={"bio": "x"}).status_code in (401, 403)


def test_read_my_profile(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    assert client.get("/doctors/me", headers=h).status_code == 404  # pas encore de fiche
    client.post("/doctors/me", json=PROFILE, headers=h)
    r = client.get("/doctors/me", headers=h)
    assert r.status_code == 200
    assert r.json()["city"] == "Tunis"


def test_update_profile_changes_only_sent_fields(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    client.post("/doctors/me", json=PROFILE, headers=h)
    r = client.put("/doctors/me", json={"bio": "Nouvelle bio"}, headers=h)
    assert r.status_code == 200
    assert r.json()["bio"] == "Nouvelle bio"
    assert r.json()["specialty"] == "Cardiologue"
    assert r.json()["consultation_duration_min"] == 25
    # la modification est bien enregistrée
    assert client.get("/doctors/me", headers=h).json()["bio"] == "Nouvelle bio"


def test_update_profile_errors(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    assert client.put("/doctors/me", json={"bio": "x"}, headers=h).status_code == 404
    client.post("/doctors/me", json=PROFILE, headers=h)
    r = client.put("/doctors/me", json={"consultation_duration_min": 500}, headers=h)
    assert r.status_code == 422


def test_doctor_only_modifies_own_profile(client, db):
    make_doctor_account(db, "a@mail.com", name="Dr A")
    make_doctor_account(db, "b@mail.com", name="Dr B")
    ha = login_header(client, "a@mail.com")
    hb = login_header(client, "b@mail.com")
    client.post("/doctors/me", json={**PROFILE, "bio": "bio de A"}, headers=ha)
    client.post("/doctors/me", json={**PROFILE, "bio": "bio de B"}, headers=hb)
    client.put("/doctors/me", json={"bio": "A a changé"}, headers=ha)
    assert client.get("/doctors/me", headers=ha).json()["bio"] == "A a changé"
    assert client.get("/doctors/me", headers=hb).json()["bio"] == "bio de B"


def test_new_profile_appears_in_public_search(client, db):
    make_doctor_account(db, "nouveau@mail.com")
    h = login_header(client, "nouveau@mail.com")
    client.post("/doctors/me", json=PROFILE, headers=h)
    r = client.get("/doctors", params={"name": "Nouveau"}, headers=patient_header(client))
    assert r.json()["total"] == 1    