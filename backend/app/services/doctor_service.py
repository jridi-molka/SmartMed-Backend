from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorListOut, DoctorOut


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