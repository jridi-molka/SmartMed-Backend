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