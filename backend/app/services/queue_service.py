from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.appointment import Appointment
from app.models.queue_entry import QueueEntry
from app.models.user import User

ACTIVE = ("waiting", "called", "in_consultation")


def compute_position(entries: list[dict], mine_id: int) -> dict:
    active = sorted(
        (e for e in entries if e["status"] in ACTIVE),
        key=lambda e: (e["start_time"], e["checked_in_at"]),
    )
    rank = next(i for i, e in enumerate(active) if e["id"] == mine_id)
    return {"position": rank + 1, "patients_before": rank}


def queue_snapshot(db: Session, entry: QueueEntry) -> dict:
    rows = db.execute(
        select(QueueEntry.id, QueueEntry.status,
               Appointment.start_time, QueueEntry.checked_in_at)
        .join(Appointment, Appointment.id == QueueEntry.appointment_id)
        .where(QueueEntry.doctor_id == entry.doctor_id,
               QueueEntry.date == entry.date)
    ).all()
    entries = [
        {"id": r.id, "status": r.status,
         "start_time": r.start_time, "checked_in_at": r.checked_in_at}
        for r in rows
    ]
    return {
        "queue_entry_id": entry.id,
        "status": entry.status,
        **compute_position(entries, entry.id),
        "estimated_wait_minutes": entry.predicted_wait_min,
        "method": None,
        "updated_at": now_local(),
    }


def check_in(db: Session, patient: User, appointment_id: int) -> dict:
    appt = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient.id,
        )
    )
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status != "booked":
        raise HTTPException(status_code=409, detail="Appointment is not active")

    now = now_local()
    if appt.date != now.date():
        raise HTTPException(status_code=409,
                            detail="Check-in only on the day of the appointment")

    if db.scalar(select(QueueEntry).where(QueueEntry.appointment_id == appt.id)):
        raise HTTPException(status_code=409, detail="Already checked in")

    entry = QueueEntry(
        appointment_id=appt.id, doctor_id=appt.doctor_id, patient_id=patient.id,
        date=appt.date, status="waiting", checked_in_at=now,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already checked in")
    db.refresh(entry)
    return queue_snapshot(db, entry)


def my_queue(db: Session, patient: User) -> dict:
    entry = db.scalar(
        select(QueueEntry)
        .where(QueueEntry.patient_id == patient.id,
               QueueEntry.date == now_local().date(),
               QueueEntry.status.in_(ACTIVE))
        .order_by(QueueEntry.checked_in_at)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Not in any queue today")
    return queue_snapshot(db, entry)