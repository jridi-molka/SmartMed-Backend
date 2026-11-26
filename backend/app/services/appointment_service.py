from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.appointment import AppointmentCreate
from app.services.slot_service import get_doctor_slots

from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.queue_entry import QueueEntry

def to_out(appt: Appointment) -> dict:
    return {
        "id": appt.id,
        "doctor": {
            "id": appt.doctor.id,
            "name": appt.doctor.user.name,
            "specialty": appt.doctor.specialty,
        },
        "date": appt.date,
        "start_time": appt.start_time,
        "end_time": appt.end_time,
        "status": appt.status,
    }


def create_appointment(db: Session, patient: User, data: AppointmentCreate) -> dict:
    # 1. Le créneau fait-il partie des créneaux proposés et disponibles ?
    result = get_doctor_slots(db, data.doctor_id, data.date)
    wanted = data.start_time.strftime("%H:%M")
    slot = next((s for s in result["slots"] if s["start_time"] == wanted), None)
    if slot is None or not slot["available"]:
        if slot is None:
            raise HTTPException(status_code=422, detail="Invalid slot")
        raise HTTPException(status_code=409, detail="Slot already taken")

    # 2. Écrire la ligne ; la base reste le juge final
    end = datetime.strptime(slot["end_time"], "%H:%M").time()
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=data.doctor_id,
        date=data.date,
        start_time=data.start_time,
        end_time=end,
        status="booked",
    )
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slot already taken")
    db.refresh(appt)
    return to_out(appt)

CANCEL_LIMIT_HOURS = 2


def list_my_appointments(db: Session, patient: User, when: str) -> list[dict]:
    rows = db.scalars(
        select(Appointment).where(Appointment.patient_id == patient.id)
    ).all()
    now = now_local()

    def start_dt(a):
        return datetime.combine(a.date, a.start_time)

    upcoming = [a for a in rows if a.status == "booked" and start_dt(a) > now]
    past = [a for a in rows if a not in upcoming]

    if when == "upcoming":
        chosen = sorted(upcoming, key=start_dt)
    else:
        chosen = sorted(past, key=start_dt, reverse=True)
    return [to_out(a) for a in chosen]


def cancel_appointment(db: Session, patient: User, appointment_id: int) -> dict:
    appt = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient.id,
        )
    )
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status != "booked":
        raise HTTPException(status_code=409, detail="Appointment cannot be cancelled")

    start = datetime.combine(appt.date, appt.start_time)
    if start - now_local() < timedelta(hours=CANCEL_LIMIT_HOURS):
        raise HTTPException(status_code=409, detail="Too late to cancel")

    appt.status = "cancelled"
    appt.cancelled_at = now_local()
    entry = db.scalar(select(QueueEntry).where(QueueEntry.appointment_id == appt.id))
    if entry is not None:
        entry.status = "skipped"
    db.commit()
    db.refresh(appt)
    return to_out(appt)