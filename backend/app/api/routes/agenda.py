import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.agenda import AgendaItemOut, StatusUpdate
from app.services import agenda_service

router = APIRouter(tags=["agenda"])


@router.get("/doctors/me/appointments", response_model=list[AgendaItemOut])
def my_agenda(
    date: dt.date | None = None,
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return agenda_service.list_agenda(db, doctor_user, date)


@router.put("/appointments/{appointment_id}/status", response_model=AgendaItemOut)
def set_status(
    appointment_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return agenda_service.change_status(db, doctor_user, appointment_id, data.status)