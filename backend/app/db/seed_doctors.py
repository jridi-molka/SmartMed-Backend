"""Remplit la base avec des médecins de démonstration.

Source : AI/data/clean/doctors_clean.csv (les 50 médecins simulés du module IA).

Utilisation (depuis le dossier backend) :
    python -m app.db.seed_doctors

Le script peut être relancé sans danger : un médecin déjà présent est ignoré.
Il n'utilise que les colonnes existantes de Doctor : aucune migration nécessaire.
"""
import csv
from datetime import time
from pathlib import Path

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.doctor import Doctor, DoctorSchedule
from app.models.user import User, UserRole

# Fichier source : dossier AI, à la racine du dépôt
CSV_PATH = (
    Path(__file__).resolve().parents[3] / "AI" / "data" / "clean" / "doctors_clean.csv"
)

DEMO_PASSWORD = "123456"   # mot de passe de démonstration, jamais en production
CITY = "Tunis"             # tous les médecins simulés sont autour de Tunis
WORK_DAYS = range(0, 5)    # 0 = lundi ... 4 = vendredi
START, END = time(9, 0), time(17, 0)


def seed(db):
    """Crée un compte + une fiche médecin + des horaires pour chaque ligne du CSV."""
    if not CSV_PATH.exists():
        raise SystemExit(f"Fichier introuvable : {CSV_PATH}")

    password_hash = hash_password(DEMO_PASSWORD)  # calculé une seule fois (plus rapide)
    created = skipped = 0

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = f"doctor{row['doctor_id']}@smartmed.test"
            if db.scalar(select(User).where(User.email == email)):
                skipped += 1
                continue

            user = User(
                name=row["name"],
                email=email,
                password_hash=password_hash,
                role=UserRole.DOCTOR,
            )
            db.add(user)
            db.flush()  # donne un id au compte

            duration = int(row["avg_consultation_min"])
            doctor = Doctor(
                user_id=user.id,
                specialty=row["specialty"],
                city=CITY,
                address=f"Cabinet médical, {CITY}",
                bio=f"{row['specialty']} - consultation d'environ {duration} minutes.",
                consultation_duration_min=duration,
            )
            db.add(doctor)
            db.flush()  # donne un id à la fiche médecin

            for weekday in WORK_DAYS:
                db.add(
                    DoctorSchedule(
                        doctor_id=doctor.id,
                        weekday=weekday,
                        start_time=START,
                        end_time=END,
                    )
                )
            created += 1

    db.commit()
    return created, skipped


if __name__ == "__main__":
    with SessionLocal() as db:
        created, skipped = seed(db)
    print(f"Médecins créés : {created} | déjà présents : {skipped}")