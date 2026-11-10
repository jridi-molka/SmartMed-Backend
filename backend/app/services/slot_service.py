from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now_local
from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorSchedule

BOOKING_WINDOW_DAYS = 30


def generate_slots(ranges, duration_min, booked_starts, now, day):
    slots = []
    for start, end in ranges:  # ex. (time(9, 0), time(12, 0))
        cur = datetime.combine(day, start)
        limit = datetime.combine(day, end)
        while cur + timedelta(minutes=duration_min) <= limit:
            nxt = cur + timedelta(minutes=duration_min)
            available = cur.time() not in booked_starts and cur > now
            slots.append({
                "start_time": cur.strftime("%H:%M"),
                "end_time": nxt.strftime("%H:%M"),
                "available": available,
            })
            cur = nxt
    return slots


def get_doctor_slots(db: Session, doctor_id: int, day: date) -> dict:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    now = now_local()
    today = now.date()
    if day < today or day > today + timedelta(days=BOOKING_WINDOW_DAYS):
        raise HTTPException(status_code=422, detail="Date out of booking window")

    rows = db.execute(
        select(DoctorSchedule.start_time, DoctorSchedule.end_time)
        .where(DoctorSchedule.doctor_id == doctor_id,
               DoctorSchedule.weekday == day.weekday())
        .order_by(DoctorSchedule.start_time)
    ).all()
    ranges = [(r.start_time, r.end_time) for r in rows]

    booked = set(db.scalars(
        select(Appointment.start_time)
        .where(Appointment.doctor_id == doctor_id,
               Appointment.date == day,
               Appointment.status == "booked")
    ))

    slots = generate_slots(ranges, doctor.consultation_duration_min, booked, now, day)
    return {"date": day, "doctor_id": doctor_id, "slots": slots}