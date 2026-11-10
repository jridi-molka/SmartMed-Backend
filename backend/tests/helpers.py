from datetime import time

from app.core.security import hash_password
from app.models.doctor import Doctor, DoctorSchedule
from app.models.user import User, UserRole


def create_doctor(db, weekday=0, start=time(9, 0), end=time(12, 0), duration=20):
    user = User(
        name="Dr Salma", email="salma@mail.com",
        password_hash=hash_password("123456"), role=UserRole.DOCTOR,
    )
    db.add(user)
    db.flush()
    doctor = Doctor(user_id=user.id, specialty="Cardiologie", city="Tunis",
                    consultation_duration_min=duration)
    db.add(doctor)
    db.flush()
    db.add(DoctorSchedule(doctor_id=doctor.id, weekday=weekday,
                          start_time=start, end_time=end))
    db.commit()
    return doctor