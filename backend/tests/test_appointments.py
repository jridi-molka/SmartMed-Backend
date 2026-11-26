from app.core.clock import now_local
from tests.helpers import create_doctor
from tests.test_auth import auth_header
from tests.test_slots_api import next_weekday
from tests.helpers import patient_header, doctor_header
from datetime import time, timedelta
from sqlalchemy.exc import IntegrityError
import pytest
from app.models.appointment import Appointment

def test_book_success(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)
    r = client.post(
        "/appointments",
        json={"doctor_id": doctor.id, "date": day.isoformat(), "start_time": "09:00"},
        headers=auth_header(client),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "booked"
    assert body["end_time"].startswith("09:20")
    assert body["doctor"]["name"] == "Dr Salma"
    assert "email" not in body["doctor"]



def book(client, doctor, day, hour, headers):
    return client.post(
        "/appointments",
        json={"doctor_id": doctor.id, "date": day.isoformat(), "start_time": hour},
        headers=headers,
    )


def test_book_already_taken(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)
    assert book(client, doctor, day, "09:00", auth_header(client)).status_code == 201
    r = book(client, doctor, day, "09:00", patient_header(client))
    assert r.status_code == 409


def test_book_invalid_slot(client, db):
    doctor = create_doctor(db, weekday=0)
    r = book(client, doctor, next_weekday(0), "09:07", auth_header(client))
    assert r.status_code == 422


def test_book_doctor_forbidden(client, db):
    doctor = create_doctor(db, weekday=0)
    r = book(client, doctor, next_weekday(0), "09:00", doctor_header(client))
    assert r.status_code == 403


def test_book_requires_token(client, db):
    doctor = create_doctor(db, weekday=0)
    r = client.post("/appointments", json={
        "doctor_id": doctor.id, "date": next_weekday(0).isoformat(), "start_time": "09:00"})
    assert r.status_code in (401, 403)


def test_slot_becomes_unavailable_after_booking(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)
    headers = auth_header(client)
    book(client, doctor, day, "09:00", headers)
    slots = client.get(f"/doctors/{doctor.id}/slots",
                       params={"date": day.isoformat()}, headers=headers).json()["slots"]
    assert slots[0]["available"] is False
    assert slots[1]["available"] is True

def test_unique_index_blocks_double_booking(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)
    patient_header(client)  # crée un utilisateur (id 2)

    def row():
        return Appointment(patient_id=1, doctor_id=doctor.id, date=day,
                           start_time=time(9, 0), end_time=time(9, 20), status="booked")

    db.add(row())
    db.commit()
    db.add(row())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_cancelled_slot_can_be_rebooked(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)

    def row(status):
        return Appointment(patient_id=1, doctor_id=doctor.id, date=day,
                           start_time=time(9, 0), end_time=time(9, 20), status=status)

    db.add(row("cancelled"))
    db.commit()
    db.add(row("booked"))
    db.commit()  # ne doit PAS lever d'erreur

def test_list_upcoming_and_cancel(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    headers = auth_header(client)
    appt_id = book(client, doctor, day, "09:00", headers).json()["id"]

    upcoming = client.get("/appointments/me", params={"when": "upcoming"}, headers=headers)
    assert [a["id"] for a in upcoming.json()] == [appt_id]

    r = client.post(f"/appointments/{appt_id}/cancel", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    assert client.get("/appointments/me", params={"when": "upcoming"}, headers=headers).json() == []
    past = client.get("/appointments/me", params={"when": "past"}, headers=headers).json()
    assert [a["id"] for a in past] == [appt_id]


def test_cancel_frees_the_slot(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    h1 = auth_header(client)
    appt_id = book(client, doctor, day, "09:00", h1).json()["id"]
    client.post(f"/appointments/{appt_id}/cancel", headers=h1)
    assert book(client, doctor, day, "09:00", patient_header(client)).status_code == 201


def test_cancel_other_patient_gets_404(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    appt_id = book(client, doctor, day, "09:00", auth_header(client)).json()["id"]
    r = client.post(f"/appointments/{appt_id}/cancel", headers=patient_header(client))
    assert r.status_code == 404


def test_cancel_twice_gets_409(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0, min_days=3)
    headers = auth_header(client)
    appt_id = book(client, doctor, day, "09:00", headers).json()["id"]
    client.post(f"/appointments/{appt_id}/cancel", headers=headers)
    assert client.post(f"/appointments/{appt_id}/cancel", headers=headers).status_code == 409


def test_cancel_too_late(client, db):
    doctor = create_doctor(db, weekday=0)
    headers = auth_header(client)  # crée le patient (id 2)
    start = now_local() + timedelta(minutes=30)
    appt = Appointment(
        patient_id=2, doctor_id=doctor.id, date=start.date(),
        start_time=start.time().replace(microsecond=0),
        end_time=(start + timedelta(minutes=20)).time().replace(microsecond=0),
        status="booked",
    )
    db.add(appt)
    db.commit()
    r = client.post(f"/appointments/{appt.id}/cancel", headers=headers)
    assert r.status_code == 409
    assert r.json()["detail"] == "Too late to cancel"


def test_list_invalid_when(client):
    r = client.get("/appointments/me", params={"when": "abc"}, headers=auth_header(client))
    assert r.status_code == 422


def test_doctor_cannot_list_or_cancel(client, db):
    create_doctor(db, weekday=0)
    h = __import__("tests.helpers", fromlist=["doctor_header"]).doctor_header(client)
    assert client.get("/appointments/me", headers=h).status_code == 403
    assert client.post("/appointments/1/cancel", headers=h).status_code == 403