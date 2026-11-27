from datetime import time, timedelta

from app.core.clock import now_local
from tests.helpers import create_doctor, doctor_header, patient_header
from tests.helpers_queue import get_user_id, insert_appointment
from tests.test_auth import auth_header


def check_in(client, appt_id, headers):
    return client.post("/queue/check-in", json={"appointment_id": appt_id},
                       headers=headers)


def setup_today(client, db):
    doctor = create_doctor(db, weekday=0)
    headers = auth_header(client)
    appt = insert_appointment(db, get_user_id(client, headers), doctor.id, time(9, 0))
    return doctor, headers, appt


def test_check_in_success(client, db):
    _, headers, appt = setup_today(client, db)
    r = check_in(client, appt.id, headers)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "waiting"
    assert body["position"] == 1
    assert body["patients_before"] == 0


def test_check_in_twice_gets_409(client, db):
    _, headers, appt = setup_today(client, db)
    check_in(client, appt.id, headers)
    assert check_in(client, appt.id, headers).status_code == 409


def test_check_in_other_day_gets_409(client, db):
    doctor = create_doctor(db, weekday=0)
    headers = auth_header(client)
    tomorrow = now_local().date() + timedelta(days=1)
    appt = insert_appointment(db, get_user_id(client, headers), doctor.id,
                              time(9, 0), day=tomorrow)
    assert check_in(client, appt.id, headers).status_code == 409


def test_check_in_cancelled_appointment_gets_409(client, db):
    doctor = create_doctor(db, weekday=0)
    headers = auth_header(client)
    appt = insert_appointment(db, get_user_id(client, headers), doctor.id,
                              time(9, 0), status="cancelled")
    assert check_in(client, appt.id, headers).status_code == 409


def test_check_in_someone_elses_appointment_gets_404(client, db):
    _, _, appt = setup_today(client, db)
    assert check_in(client, appt.id, patient_header(client)).status_code == 404


def test_my_queue_when_not_in_queue(client, db):
    create_doctor(db, weekday=0)
    r = client.get("/queue/me", headers=auth_header(client))
    assert r.status_code == 404


def test_position_follows_appointment_order(client, db):
    doctor = create_doctor(db, weekday=0)
    ha, hb = auth_header(client), patient_header(client)
    a = insert_appointment(db, get_user_id(client, ha), doctor.id, time(9, 0))
    b = insert_appointment(db, get_user_id(client, hb), doctor.id, time(9, 20))
    check_in(client, b.id, hb)   # B arrive en premier
    check_in(client, a.id, ha)   # A arrive ensuite, mais son RDV est plus tôt
    ra = client.get("/queue/me", headers=ha).json()
    rb = client.get("/queue/me", headers=hb).json()
    assert (ra["position"], ra["patients_before"]) == (1, 0)
    assert (rb["position"], rb["patients_before"]) == (2, 1)


def test_doctor_cannot_check_in(client, db):
    _, _, appt = setup_today(client, db)
    assert check_in(client, appt.id, doctor_header(client)).status_code == 403