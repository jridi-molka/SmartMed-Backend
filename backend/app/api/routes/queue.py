
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.queue import CheckInIn, QueueStatusOut
from app.services import queue_service

from app.schemas.queue import QueueEntryOut

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

@router.get("/doctor", response_model=list[QueueEntryOut])
def doctor_queue(
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return queue_service.list_doctor_queue(db, doctor_user)


@router.post("/call-next", response_model=QueueEntryOut)
def call_next(
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return queue_service.call_next(db, doctor_user)


@router.post("/{entry_id}/start", response_model=QueueEntryOut)
def start(
    entry_id: int,
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return queue_service.start_consultation(db, doctor_user, entry_id)


@router.post("/{entry_id}/finish", response_model=QueueEntryOut)
def finish(
    entry_id: int,
    db: Session = Depends(get_db),
    doctor_user: User = Depends(require_role("doctor")),
):
    return queue_service.finish_consultation(db, doctor_user, entry_id)