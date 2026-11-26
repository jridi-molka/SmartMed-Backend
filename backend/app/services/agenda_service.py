import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User

ALLOWED = {
    "booked": {"completed", "no_show", "cancelled"},
    "completed": set(),
    "no_show": set(),
    "cancelled": set(),
}


def get_my_doctor(db: Session, user: User) -> Doctor:
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return doctor


def to_agenda_item(appt: Appointment) -> dict:
    return {
        "id": appt.id,
        "patient_name": appt.patient.name,
        "date": appt.date,
        "start_time": appt.start_time,
        "end_time": appt.end_time,
        "status": appt.status,
    }


def list_agenda(db: Session, user: User, day: dt.date | None) -> list[dict]:
    doctor = get_my_doctor(db, user)
    day = day or now_local().date()
    rows = db.scalars(
        select(Appointment)
        .where(Appointment.doctor_id == doctor.id, Appointment.date == day)
        .order_by(Appointment.start_time)
    ).all()
    return [to_agenda_item(a) for a in rows]


def change_status(db: Session, user: User, appointment_id: int, new: str) -> dict:
    doctor = get_my_doctor(db, user)
    appt = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.doctor_id == doctor.id,
        )
    )
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if new not in ALLOWED[appt.status]:
        raise HTTPException(status_code=409, detail="Invalid status transition")
    appt.status = new
    db.commit()
    db.refresh(appt)
    return to_agenda_item(appt)