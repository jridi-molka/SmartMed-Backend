import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.appointment import SlotsOut
from app.services import slot_service

router = APIRouter(prefix="/doctors", tags=["slots"])


@router.get("/{doctor_id}/slots", response_model=SlotsOut)
def read_slots(
    doctor_id: int,
    date: dt.date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return slot_service.get_doctor_slots(db, doctor_id, date)