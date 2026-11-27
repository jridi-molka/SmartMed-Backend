from datetime import datetime, time, timedelta

import pytest

from app.core.clock import now_local
from app.models.queue_entry import QueueEntry
from app.services import wait_time_service as wts
from app.services.wait_time_service import estimate_wait, round_to_5
from tests.helpers import create_doctor
from tests.helpers_queue import get_user_id, insert_appointment
from tests.test_queue_doctor import call_next, setup_queue
from tests.test_queue_patient import check_in, setup_today
from tests.helpers import doctor_header, patient_header
from tests.test_auth import auth_header


def _boom(**kwargs):
    raise RuntimeError("model down")


def add_done_entry(db, doctor, start, minutes, patients_before=0):
    appt = insert_appointment(db, doctor.user_id, doctor.id, start, status="completed")
    begun = now_local() - timedelta(minutes=60)
    db.add(QueueEntry(
        appointment_id=appt.id, doctor_id=doctor.id, patient_id=doctor.user_id,
        date=appt.date, status="done", patients_before=patients_before,
        checked_in_at=begun - timedelta(minutes=5),
        started_at=begun, ended_at=begun + timedelta(minutes=minutes),
    ))
    db.commit()


@pytest.mark.parametrize("raw, expected", [(2, 0), (3, 5), (58, 60), (62, 60), (63, 65)])
def test_round_to_5(raw, expected):
    assert round_to_5(raw) == expected


def test_model_used_when_valid(db, monkeypatch):
    doctor = create_doctor(db)
    monkeypatch.setattr(wts, "call_model", lambda **kw: 58)
    assert estimate_wait(db, doctor, 3) == (60, "model")


def test_formula_when_model_crashes(db, monkeypatch):
    doctor = create_doctor(db)
    monkeypatch.setattr(wts, "call_model", _boom)
    assert estimate_wait(db, doctor, 3) == (60, "formula")


def test_formula_when_module_missing(db, monkeypatch):
    doctor = create_doctor(db)

    def missing(**kw):
        raise ImportError("no module named waiting_time")

    monkeypatch.setattr(wts, "call_model", missing)
    assert estimate_wait(db, doctor, 2) == (40, "formula")


def test_formula_when_prediction_negative(db, monkeypatch):
    doctor = create_doctor(db)
    monkeypatch.setattr(wts, "call_model", lambda **kw: -5)
    assert estimate_wait(db, doctor, 3) == (60, "formula")


def test_formula_when_prediction_too_high(db, monkeypatch):
    doctor = create_doctor(db)
    monkeypatch.setattr(wts, "call_model", lambda **kw: 500)
    assert estimate_wait(db, doctor, 3) == (60, "formula")


def test_model_receives_named_inputs(db, monkeypatch):
    doctor = create_doctor(db, duration=20)
    seen = {}

    def spy(**kw):
        seen.update(kw)
        return 40

    monkeypatch.setattr(wts, "call_model", spy)
    estimate_wait(db, doctor, 2)
    assert seen["patients_before"] == 2
    assert seen["avg_consultation_min"] == 20
    assert seen["doctor_avg_delay_min"] == 0.0
    assert set(seen) == {"patients_before", "avg_consultation_min", "hour_of_day",
                         "day_of_week", "doctor_avg_delay_min"}


def test_measured_duration_used_after_three_done(db, monkeypatch):
    doctor = create_doctor(db, duration=20)
    for h in (9, 10, 11):
        add_done_entry(db, doctor, time(h, 0), 10)
    monkeypatch.setattr(wts, "call_model", _boom)
    assert estimate_wait(db, doctor, 2) == (20, "formula")   # 2 x 10 mesurées


def test_declared_duration_kept_with_only_two_done(db, monkeypatch):
    doctor = create_doctor(db, duration=20)
    for h in (9, 10):
        add_done_entry(db, doctor, time(h, 0), 10)
    monkeypatch.setattr(wts, "call_model", _boom)
    assert estimate_wait(db, doctor, 2) == (40, "formula")   # 2 x 20 déclarées


def test_delay_is_zero_without_history(db):
    doctor = create_doctor(db)
    assert wts.doctor_avg_delay(db, doctor, 20, now_local()) == 0.0


def test_delay_computed_like_the_ai_data(db):
    doctor = create_doctor(db)
    appt = insert_appointment(db, doctor.user_id, doctor.id, time(9, 0),
                              status="completed")
    db.add(QueueEntry(
        appointment_id=appt.id, doctor_id=doctor.id, patient_id=doctor.user_id,
        date=appt.date, status="done", patients_before=2,
        checked_in_at=datetime.combine(appt.date, time(8, 0)),
        started_at=datetime.combine(appt.date, time(8, 50)),   # attente réelle : 50
        ended_at=datetime.combine(appt.date, time(9, 10)),
    ))
    db.commit()
    # 50 - 2 x 20 = 10
    assert wts.doctor_avg_delay(db, doctor, 20, now_local()) == 10.0


def test_check_in_stores_prediction(client, db, monkeypatch):
    monkeypatch.setattr(wts, "call_model", lambda **kw: 58)
    _, headers, appt = setup_today(client, db)
    body = check_in(client, appt.id, headers).json()
    assert body["estimated_wait_minutes"] == 60
    assert body["method"] == "model"
    assert db.get(QueueEntry, body["queue_entry_id"]).predicted_wait_min == 60


def test_check_in_stores_patients_before(client, db, monkeypatch):
    monkeypatch.setattr(wts, "call_model", lambda **kw: 58)
    doctor = create_doctor(db, weekday=0)
    ha, hb = auth_header(client), patient_header(client)
    a = insert_appointment(db, get_user_id(client, ha), doctor.id, time(9, 0))
    b = insert_appointment(db, get_user_id(client, hb), doctor.id, time(9, 20))
    check_in(client, a.id, ha)
    body = check_in(client, b.id, hb).json()          # A est devant B
    assert body["patients_before"] == 1
    assert db.get(QueueEntry, body["queue_entry_id"]).patients_before == 1


def test_api_still_works_when_model_is_down(client, db, monkeypatch):
    monkeypatch.setattr(wts, "call_model", _boom)
    _, hb, _, _ = setup_queue(client, db)   # Karim : 1 patient devant lui
    body = client.get("/queue/me", headers=hb).json()
    assert body["patients_before"] == 1
    assert body["estimated_wait_minutes"] == 20
    assert body["method"] == "formula"


def test_called_patient_has_zero_wait(client, db, monkeypatch):
    monkeypatch.setattr(wts, "call_model", lambda **kw: 58)
    ha, _, _, _ = setup_queue(client, db)
    call_next(client, doctor_header(client))
    body = client.get("/queue/me", headers=ha).json()
    assert body["status"] == "called"
    assert body["estimated_wait_minutes"] == 0
    assert body["method"] is None