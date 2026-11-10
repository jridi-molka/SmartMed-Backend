from datetime import timedelta

from app.core.clock import now_local
from tests.helpers import create_doctor
from tests.test_auth import auth_header


def next_weekday(weekday, min_days=1):
    d = now_local().date() + timedelta(days=min_days)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


def test_slots_nominal(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(0)
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": day.isoformat()},
                   headers=auth_header(client))
    assert r.status_code == 200
    assert len(r.json()["slots"]) == 9
    assert r.json()["slots"][0]["available"] is True


def test_slots_day_without_schedule(client, db):
    doctor = create_doctor(db, weekday=0)
    day = next_weekday(1)  # mardi
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": day.isoformat()},
                   headers=auth_header(client))
    assert r.status_code == 200
    assert r.json()["slots"] == []


def test_slots_unknown_doctor(client):
    day = next_weekday(0)
    r = client.get("/doctors/9999/slots", params={"date": day.isoformat()},
                   headers=auth_header(client))
    assert r.status_code == 404


def test_slots_past_date(client, db):
    doctor = create_doctor(db)
    past = now_local().date() - timedelta(days=1)
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": past.isoformat()},
                   headers=auth_header(client))
    assert r.status_code == 422


def test_slots_too_far(client, db):
    doctor = create_doctor(db)
    far = now_local().date() + timedelta(days=31)
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": far.isoformat()},
                   headers=auth_header(client))
    assert r.status_code == 422


def test_slots_invalid_date_format(client, db):
    doctor = create_doctor(db)
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": "abc"},
                   headers=auth_header(client))
    assert r.status_code == 422


def test_slots_requires_token(client, db):
    doctor = create_doctor(db)
    r = client.get(f"/doctors/{doctor.id}/slots", params={"date": "2026-12-01"})
    assert r.status_code in (401, 403)