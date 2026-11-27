from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.queue import CheckInIn, QueueStatusOut
from app.services import queue_service

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/check-in", response_model=QueueStatusOut,
             status_code=status.HTTP_201_CREATED)
def check_in(
    data: CheckInIn,
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("patient")),
):
    return queue_service.check_in(db, patient, data.appointment_id)


@router.get("/me", response_model=QueueStatusOut)
def my_queue(
    db: Session = Depends(get_db),
    patient: User = Depends(require_role("patient")),
):
    return queue_service.my_queue(db, patient)