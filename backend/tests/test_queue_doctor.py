from datetime import time

from tests.helpers import create_doctor, doctor_header, patient_header
from tests.helpers_queue import get_user_id, insert_appointment
from tests.test_agenda import other_doctor_header
from tests.test_auth import auth_header
from tests.test_queue_patient import check_in


def setup_queue(client, db):
    """Sarra (RDV 09:00) et Karim (RDV 09:20). Karim arrive AVANT Sarra."""
    doctor = create_doctor(db, weekday=0)
    ha, hb = auth_header(client), patient_header(client)
    a = insert_appointment(db, get_user_id(client, ha), doctor.id, time(9, 0))
    b = insert_appointment(db, get_user_id(client, hb), doctor.id, time(9, 20))
    eb = check_in(client, b.id, hb).json()["queue_entry_id"]
    ea = check_in(client, a.id, ha).json()["queue_entry_id"]
    return ha, hb, ea, eb


def call_next(client, headers):
    return client.post("/queue/call-next", headers=headers)


def test_doctor_queue_ordered_without_email(client, db):
    setup_queue(client, db)
    r = client.get("/queue/doctor", headers=doctor_header(client))
    assert r.status_code == 200
    assert [i["patient_name"] for i in r.json()] == ["Sarra", "Karim"]
    assert all("email" not in i for i in r.json())


def test_call_next_follows_appointment_order(client, db):
    setup_queue(client, db)
    r = call_next(client, doctor_header(client))
    assert r.status_code == 200
    assert r.json()["patient_name"] == "Sarra"   # RDV 09:00, même si arrivée après
    assert r.json()["status"] == "called"
    assert r.json()["called_at"] is not None


def test_call_next_twice_calls_two_different_patients(client, db):
    setup_queue(client, db)
    dh = doctor_header(client)
    assert call_next(client, dh).json()["patient_name"] == "Sarra"
    assert call_next(client, dh).json()["patient_name"] == "Karim"
    assert call_next(client, dh).status_code == 404


def test_call_next_empty_queue(client, db):
    create_doctor(db, weekday=0)
    r = call_next(client, doctor_header(client))
    assert r.status_code == 404
    assert r.json()["detail"] == "Queue is empty"


def test_patient_sees_called_status_and_positions(client, db):
    ha, hb, _, _ = setup_queue(client, db)
    call_next(client, doctor_header(client))
    a = client.get("/queue/me", headers=ha).json()
    b = client.get("/queue/me", headers=hb).json()
    assert a["status"] == "called"
    assert (a["position"], a["patients_before"]) == (1, 0)
    assert (b["position"], b["patients_before"]) == (2, 1)


def test_full_consultation_flow(client, db):
    ha, _, _, _ = setup_queue(client, db)
    dh = doctor_header(client)
    entry_id = call_next(client, dh).json()["id"]

    r = client.post(f"/queue/{entry_id}/start", headers=dh)
    assert r.status_code == 200
    assert r.json()["status"] == "in_consultation"
    assert r.json()["started_at"] is not None

    r = client.post(f"/queue/{entry_id}/finish", headers=dh)
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["ended_at"] is not None

    past = client.get("/appointments/me", params={"when": "past"}, headers=ha).json()
    assert [a["status"] for a in past] == ["completed"]
    assert client.get("/queue/me", headers=ha).status_code == 404


def test_start_before_call_gets_409(client, db):
    _, _, ea, _ = setup_queue(client, db)
    r = client.post(f"/queue/{ea}/start", headers=doctor_header(client))
    assert r.status_code == 409


def test_finish_before_start_gets_409(client, db):
    _, _, ea, _ = setup_queue(client, db)
    r = client.post(f"/queue/{ea}/finish", headers=doctor_header(client))
    assert r.status_code == 409


def test_start_twice_gets_409(client, db):
    setup_queue(client, db)
    dh = doctor_header(client)
    entry_id = call_next(client, dh).json()["id"]
    client.post(f"/queue/{entry_id}/start", headers=dh)
    assert client.post(f"/queue/{entry_id}/start", headers=dh).status_code == 409


def test_other_doctor_gets_404(client, db):
    _, _, ea, _ = setup_queue(client, db)
    r = client.post(f"/queue/{ea}/start", headers=other_doctor_header(client, db))
    assert r.status_code == 404


def test_patient_cannot_use_doctor_routes(client, db):
    ha, _, ea, _ = setup_queue(client, db)
    assert client.get("/queue/doctor", headers=ha).status_code == 403
    assert call_next(client, ha).status_code == 403
    assert client.post(f"/queue/{ea}/start", headers=ha).status_code == 403
    assert client.post(f"/queue/{ea}/finish", headers=ha).status_code == 403