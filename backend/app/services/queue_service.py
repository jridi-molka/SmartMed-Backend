from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.appointment import Appointment
from app.models.queue_entry import QueueEntry
from app.models.user import User

from app.services.agenda_service import get_my_doctor

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

QUEUE_ALLOWED = {
    "waiting": {"called", "skipped"},
    "called": {"in_consultation", "skipped"},
    "in_consultation": {"done"},
    "done": set(),
    "skipped": set(),
}


def item_for(db: Session, entry: QueueEntry) -> dict:
    appt = db.get(Appointment, entry.appointment_id)
    patient = db.get(User, entry.patient_id)
    return {
        "id": entry.id,
        "patient_name": patient.name,
        "appointment_time": appt.start_time,
        "status": entry.status,
        "checked_in_at": entry.checked_in_at,
        "called_at": entry.called_at,
        "started_at": entry.started_at,
        "ended_at": entry.ended_at,
    }


def list_doctor_queue(db: Session, user: User) -> list[dict]:
    doctor = get_my_doctor(db, user)
    entries = db.scalars(
        select(QueueEntry)
        .join(Appointment, Appointment.id == QueueEntry.appointment_id)
        .where(QueueEntry.doctor_id == doctor.id,
               QueueEntry.date == now_local().date())
        .order_by(Appointment.start_time, QueueEntry.checked_in_at)
    ).all()
    return [item_for(db, e) for e in entries]


def call_next(db: Session, user: User) -> dict:
    doctor = get_my_doctor(db, user)
    entry = db.scalar(
        select(QueueEntry)
        .join(Appointment, Appointment.id == QueueEntry.appointment_id)
        .where(QueueEntry.doctor_id == doctor.id,
               QueueEntry.date == now_local().date(),
               QueueEntry.status == "waiting")
        .order_by(Appointment.start_time, QueueEntry.checked_in_at)
        .limit(1)
        .with_for_update(of=QueueEntry)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Queue is empty")
    entry.status = "called"
    entry.called_at = now_local()
    db.commit()
    return item_for(db, entry)


def _my_entry(db: Session, user: User, entry_id: int) -> QueueEntry:
    doctor = get_my_doctor(db, user)
    entry = db.scalar(
        select(QueueEntry).where(QueueEntry.id == entry_id,
                                 QueueEntry.doctor_id == doctor.id)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return entry


def _check(entry: QueueEntry, new: str) -> None:
    if new not in QUEUE_ALLOWED[entry.status]:
        raise HTTPException(status_code=409, detail="Invalid status transition")


def start_consultation(db: Session, user: User, entry_id: int) -> dict:
    entry = _my_entry(db, user, entry_id)
    _check(entry, "in_consultation")
    entry.status = "in_consultation"
    entry.started_at = now_local()
    db.commit()
    return item_for(db, entry)


def finish_consultation(db: Session, user: User, entry_id: int) -> dict:
    entry = _my_entry(db, user, entry_id)
    _check(entry, "done")
    entry.status = "done"
    entry.ended_at = now_local()
    appt = db.get(Appointment, entry.appointment_id)
    appt.status = "completed"
    db.commit()
    return item_for(db, entry)