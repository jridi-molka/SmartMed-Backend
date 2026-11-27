from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorListOut, DoctorOut, DoctorUpdate


def _to_out(doctor: Doctor, name: str) -> DoctorOut:
    """Transforme une fiche médecin + son nom en réponse API."""
    return DoctorOut(
        id=doctor.id,
        user_id=doctor.user_id,
        name=name,
        specialty=doctor.specialty,
        bio=doctor.bio,
        address=doctor.address,
        city=doctor.city,
        consultation_duration_min=doctor.consultation_duration_min,
    )


def search_doctors(
    db: Session,
    specialty: str | None = None,
    city: str | None = None,
    name: str | None = None,
    sort: str = "name",
    skip: int = 0,
    limit: int = 20,
) -> DoctorListOut:
    # Le nom du médecin est dans la table users : on relie les deux tables.
    query = select(Doctor, User.name).join(User, Doctor.user_id == User.id)

    # Chaque filtre n'est ajouté que s'il est fourni.
    if specialty:
        query = query.where(func.lower(Doctor.specialty) == specialty.lower())
    if city:
        query = query.where(func.lower(Doctor.city) == city.lower())
    if name:
        query = query.where(User.name.ilike(f"%{name}%"))

    # Nombre total de résultats, avant la pagination.
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    order = User.name.desc() if sort == "-name" else User.name.asc()
    rows = db.execute(query.order_by(order).offset(skip).limit(limit)).all()
    return DoctorListOut(items=[_to_out(d, n) for d, n in rows], total=total)


def list_specialties(db: Session) -> list[str]:
    """Liste des spécialités présentes en base, sans doublon, triée."""
    stmt = select(Doctor.specialty).distinct().order_by(Doctor.specialty)
    return list(db.scalars(stmt).all())


def get_doctor(db: Session, doctor_id: int) -> DoctorOut:
    """Renvoie la fiche d'un médecin, ou une erreur 404 s'il n'existe pas."""
    row = db.execute(
        select(Doctor, User.name)
        .join(User, Doctor.user_id == User.id)
        .where(Doctor.id == doctor_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Médecin introuvable")
    doctor, name = row
    return _to_out(doctor, name)

def _get_my_doctor(db: Session, user: User) -> Doctor:
    """Cherche la fiche du médecin connecté (404 s'il n'en a pas encore)."""
    doctor = db.scalar(select(Doctor).where(Doctor.user_id == user.id))
    if doctor is None:
        raise HTTPException(status_code=404, detail="Profil médecin introuvable")
    return doctor


def create_my_profile(db: Session, user: User, data: DoctorCreate) -> DoctorOut:
    """Crée la fiche du médecin connecté (409 s'il en a déjà une)."""
    if db.scalar(select(Doctor).where(Doctor.user_id == user.id)):
        raise HTTPException(status_code=409, detail="Profil médecin déjà créé")
    doctor = Doctor(user_id=user.id, **data.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return _to_out(doctor, user.name)


def get_my_profile(db: Session, user: User) -> DoctorOut:
    return _to_out(_get_my_doctor(db, user), user.name)


def update_my_profile(db: Session, user: User, data: DoctorUpdate) -> DoctorOut:
    """Modifie seulement les champs envoyés."""
    doctor = _get_my_doctor(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        # la spécialité et la durée sont obligatoires : on ignore un null
        if value is None and field in ("specialty", "consultation_duration_min"):
            continue
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return _to_out(doctor, user.name)