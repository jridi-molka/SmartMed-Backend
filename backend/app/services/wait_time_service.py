import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.doctor import Doctor
from app.models.queue_entry import QueueEntry

AI_DIR = Path(__file__).resolve().parents[3] / "AI"
if str(AI_DIR) not in sys.path:
    sys.path.append(str(AI_DIR))

MIN_DONE_FOR_MEASURE = 3
DELAY_WINDOW_DAYS = 30
MAX_WAIT_MIN = 240


def call_model(patients_before, avg_consultation_min, hour_of_day,
               day_of_week, doctor_avg_delay_min):
    from waiting_time.predict import predict_wait_time
    return predict_wait_time(
        patients_before=patients_before,
        avg_consultation_min=avg_consultation_min,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        doctor_avg_delay_min=doctor_avg_delay_min,
    )


def round_to_5(minutes: float) -> int:
    return int((minutes + 2.5) // 5 * 5)


def measured_avg_duration(db: Session, doctor: Doctor, today) -> float | None:
    rows = db.execute(
        select(QueueEntry.started_at, QueueEntry.ended_at).where(
            QueueEntry.doctor_id == doctor.id,
            QueueEntry.date == today,
            QueueEntry.status == "done",
        )
    ).all()
    durations = [(r.ended_at - r.started_at).total_seconds() / 60
                 for r in rows if r.started_at and r.ended_at]
    if len(durations) < MIN_DONE_FOR_MEASURE:
        return None
    return sum(durations) / len(durations)


def doctor_avg_delay(db: Session, doctor: Doctor, avg: float, now: datetime) -> float:
    since = now.date() - timedelta(days=DELAY_WINDOW_DAYS)
    rows = db.execute(
        select(QueueEntry.checked_in_at, QueueEntry.started_at,
               QueueEntry.patients_before)
        .where(QueueEntry.doctor_id == doctor.id,
               QueueEntry.date >= since,
               QueueEntry.started_at.is_not(None),
               QueueEntry.patients_before.is_not(None))
    ).all()
    delays = [
        (r.started_at - r.checked_in_at).total_seconds() / 60 - r.patients_before * avg
        for r in rows
    ]
    return sum(delays) / len(delays) if delays else 0.0


def current_elapsed(db: Session, doctor: Doctor, now: datetime) -> float:
    started = db.scalar(
        select(QueueEntry.started_at).where(
            QueueEntry.doctor_id == doctor.id,
            QueueEntry.date == now.date(),
            QueueEntry.status == "in_consultation",
        )
    )
    if started is None:
        return 0.0
    return max(0.0, (now - started).total_seconds() / 60)


def estimate_wait(db: Session, doctor: Doctor, patients_before: int,
                  now: datetime | None = None) -> tuple[int, str]:
    now = now or now_local()
    avg = measured_avg_duration(db, doctor, now.date()) or doctor.consultation_duration_min
    delay = doctor_avg_delay(db, doctor, avg, now)

    spent = min(current_elapsed(db, doctor, now), avg) if patients_before >= 1 else 0.0
    baseline = max(0.0, patients_before * avg - spent)

    try:
        minutes = call_model(
            patients_before=patients_before,
            avg_consultation_min=avg,
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            doctor_avg_delay_min=delay,
        )
        if not (0 <= minutes <= MAX_WAIT_MIN):
            raise ValueError("prediction out of range")
        return round_to_5(minutes), "model"
    except Exception:
        return round_to_5(baseline), "formula"