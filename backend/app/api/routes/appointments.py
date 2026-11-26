from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentOut
from app.services import appointment_service

from typing import Literal

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("patient")),
):
    return appointment_service.create_appointment(db, patient, data)



@router.get("/me", response_model=list[AppointmentOut])
def my_appointments(
    when: Literal["upcoming", "past"] = "upcoming",
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("patient")),
):
    return appointment_service.list_my_appointments(db, patient, when)


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: int,
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("patient")),
):
    return appointment_service.cancel_appointment(db, patient, appointment_id)