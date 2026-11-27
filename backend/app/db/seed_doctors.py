"""Remplit la base avec des médecins de démonstration.

Source : AI/data/clean/doctors_clean.csv (les 50 médecins simulés du module IA).

Utilisation (depuis le dossier backend) :
    SEED_DOCTOR_PASSWORD=<mot de passe de démo> python -m app.db.seed_doctors

Le mot de passe n'est jamais écrit dans le code : il vient de la variable
d'environnement SEED_DOCTOR_PASSWORD.

Le script peut être relancé sans danger : un médecin déjà présent n'est pas
recréé (sa ville est seulement remise à jour).
Il n'utilise que les colonnes existantes de Doctor : aucune migration nécessaire.
"""
import csv
import os
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

# ".test" est refusé par la validation des e-mails : on utilise un vrai domaine.
EMAIL_DOMAIN = "smartmed-demo.com"
# Villes (simulées) réparties entre les médecins, pour pouvoir démontrer le filtre.
CITIES = ["Tunis", "Sfax", "Sousse"]
WORK_DAYS = range(0, 5)    # 0 = lundi ... 4 = vendredi
START, END = time(9, 0), time(17, 0)


def seed(db, password):
    """Crée un compte + une fiche médecin + des horaires pour chaque ligne du CSV."""
    if not CSV_PATH.exists():
        raise SystemExit(f"Fichier introuvable : {CSV_PATH}")

    password_hash = hash_password(password)  # calculé une seule fois (plus rapide)
    created = skipped = 0

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            doctor_id = int(row["doctor_id"])
            email = f"doctor{doctor_id}@{EMAIL_DOMAIN}"
            city = CITIES[(doctor_id - 1) % len(CITIES)]

            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                doctor = db.scalar(select(Doctor).where(Doctor.user_id == existing.id))
                if doctor:
                    doctor.city = city  # remet la ville à jour, sans doublon
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
                city=city,
                address=f"Cabinet médical, {city}",
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
    password = os.environ.get("SEED_DOCTOR_PASSWORD")
    if not password:
        raise SystemExit(
            "Définis d'abord le mot de passe de démo : "
            "SEED_DOCTOR_PASSWORD=... python -m app.db.seed_doctors"
        )
    with SessionLocal() as db:
        created, skipped = seed(db, password)
    print(f"Médecins créés : {created} | déjà présents : {skipped}")