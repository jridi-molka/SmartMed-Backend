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