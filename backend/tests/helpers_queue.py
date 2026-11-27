from datetime import datetime, timedelta

from app.core.clock import now_local
from app.models.appointment import Appointment


def get_user_id(client, headers) -> int:
    return client.get("/users/me", headers=headers).json()["id"]


def insert_appointment(db, patient_id, doctor_id, start, day=None, status="booked"):
    day = day or now_local().date()
    end = (datetime.combine(day, start) + timedelta(minutes=20)).time()
    appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, date=day,
                       start_time=start, end_time=end, status=status)
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt