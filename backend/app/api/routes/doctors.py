from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.doctor import DoctorListOut, DoctorOut
from app.services import doctor_service

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



@router.get("/{doctor_id}", response_model=DoctorOut)
def read_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return doctor_service.get_doctor(db, doctor_id)