from datetime import datetime, time

from app.services.queue_service import compute_position


def entry(id, status, start, arrived):
    return {"id": id, "status": status, "start_time": start,
            "checked_in_at": arrived}


T = lambda h, m: datetime(2026, 12, 1, h, m)


def test_order_follows_appointment_then_arrival():
    entries = [
        entry(1, "waiting", time(9, 0), T(8, 50)),
        entry(2, "waiting", time(9, 0), T(8, 40)),   # même heure, arrivé avant
        entry(3, "waiting", time(9, 20), T(8, 30)),  # arrivé le premier, mais RDV plus tard
        entry(4, "waiting", time(9, 40), T(9, 0)),
    ]
    assert compute_position(entries, 2) == {"position": 1, "patients_before": 0}
    assert compute_position(entries, 1) == {"position": 2, "patients_before": 1}
    assert compute_position(entries, 3) == {"position": 3, "patients_before": 2}
    assert compute_position(entries, 4) == {"position": 4, "patients_before": 3}


def test_done_and_skipped_do_not_count():
    entries = [
        entry(1, "done", time(9, 0), T(8, 50)),
        entry(2, "skipped", time(9, 20), T(9, 0)),
        entry(3, "waiting", time(9, 40), T(9, 30)),
    ]
    assert compute_position(entries, 3) == {"position": 1, "patients_before": 0}


def test_in_consultation_counts_as_before():
    entries = [
        entry(1, "in_consultation", time(9, 0), T(8, 50)),
        entry(2, "waiting", time(9, 20), T(9, 0)),
    ]
    assert compute_position(entries, 2) == {"position": 2, "patients_before": 1}