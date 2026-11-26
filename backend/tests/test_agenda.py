from app.core.security import hash_password
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from tests.helpers import create_doctor, doctor_header, patient_header
from tests.test_appointments import book
from tests.test_auth import auth_header
from tests.test_slots_api import next_weekday


def other_doctor_header(client, db):
    user = User(name="Dr Karim", email="karim.doc@mail.com",
                password_hash=hash_password("123456"), role=UserRole.DOCTOR)
    db.add(user)
    db.flush()
    db.add(Doctor(user_id=user.id, specialty="Dermatologue", city="Tunis",
                  consultation_duration_min=20))
    db.commit()
    token = client.post("/auth/login", json={"email": "karim.doc@mail.com",
                                              "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_agenda_sorted_and_no_email(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    book(client, doctor, day, "09:20", auth_header(client))
    book(client, doctor, day, "09:00", patient_header(client))
    r = client.get("/doctors/me/appointments", params={"date": day.isoformat()},
                   headers=doctor_header(client))
    assert r.status_code == 200
    items = r.json()
    assert [i["start_time"][:5] for i in items] == ["09:00", "09:20"]
    assert items[0]["patient_name"] == "Karim"
    assert all("email" not in i for i in items)


def test_agenda_default_date_is_today(client, db):
    create_doctor(db, weekday=0)
    r = client.get("/doctors/me/appointments", headers=doctor_header(client))
    assert r.status_code == 200
    assert r.json() == []


def test_patient_cannot_read_agenda(client, db):
    create_doctor(db, weekday=0)
    r = client.get("/doctors/me/appointments", headers=auth_header(client))
    assert r.status_code == 403


def test_mark_completed(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "completed"},
                   headers=doctor_header(client))
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_mark_no_show(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "no_show"},
                   headers=doctor_header(client))
    assert r.json()["status"] == "no_show"


def test_final_status_cannot_change(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    h = doctor_header(client)
    client.put(f"/appointments/{appt_id}/status", json={"status": "completed"}, headers=h)
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "no_show"}, headers=h)
    assert r.status_code == 409


def test_cannot_change_cancelled_appointment(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    headers = auth_header(client)
    appt_id = book(client, doctor, day, "09:00", headers).json()["id"]
    client.post(f"/appointments/{appt_id}/cancel", headers=headers)
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "completed"},
                   headers=doctor_header(client))
    assert r.status_code == 409


def test_other_doctor_gets_404(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "completed"},
                   headers=other_doctor_header(client, db))
    assert r.status_code == 404


def test_invalid_status_value(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "cancelled"},
                   headers=doctor_header(client))
    assert r.status_code == 422


def test_patient_cannot_change_status(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    headers = auth_header(client)
    appt_id = book(client, doctor, day, "09:00", headers).json()["id"]
    r = client.put(f"/appointments/{appt_id}/status", json={"status": "completed"},
                   headers=headers)
    assert r.status_code == 403