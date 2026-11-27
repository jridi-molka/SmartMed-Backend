from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorListOut, DoctorOut, DoctorUpdate
from app.services import doctor_service
from app.schemas.schedule import ScheduleIn, ScheduleOut

router = APIRouter(prefix="/doctors", tags=["doctors"])


# Cette route doit rester AVANT toute route "/{doctor_id}" (ajoutée plus tard) :
# sinon FastAPI prendrait "specialties" pour un identifiant de médecin.
@router.get("/specialties", response_model=list[str])
def read_specialties(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return doctor_service.list_specialties(db)


@router.get("", response_model=DoctorListOut)
def read_doctors(
    specialty: str | None = None,
    city: str | None = None,
    name: str | None = None,
    sort: Literal["name", "-name"] = "name",
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return doctor_service.search_doctors(db, specialty, city, name, sort, skip, limit)




@router.post("/me", response_model=DoctorOut, status_code=201)
def create_my_profile(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    return doctor_service.create_my_profile(db, user, data)


@router.get("/me", response_model=DoctorOut)
def read_my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    return doctor_service.get_my_profile(db, user)


@router.put("/me", response_model=DoctorOut)
def update_my_profile(
    data: DoctorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    return doctor_service.update_my_profile(db, user, data)



@router.get("/me/schedule", response_model=ScheduleOut)
def read_my_schedule(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    return doctor_service.get_my_schedule(db, user)


@router.put("/me/schedule", response_model=ScheduleOut)
def replace_my_schedule(
    data: ScheduleIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("doctor")),
):
    return doctor_service.replace_my_schedule(db, user, data)









@router.get("/{doctor_id}", response_model=DoctorOut)
def read_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return doctor_service.get_doctor(db, doctor_id)



@router.get("/{doctor_id}/schedule", response_model=ScheduleOut)
def read_doctor_schedule(
    doctor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return doctor_service.get_doctor_schedule(db, doctor_id)