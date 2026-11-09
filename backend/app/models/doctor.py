from datetime import datetime, time

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    specialty: Mapped[str] = mapped_column(String(100), index=True)
    bio: Mapped[str | None] = mapped_column(String(1000))
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    consultation_duration_min: Mapped[int] = mapped_column(default=20)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User")
    schedules = relationship(
        "DoctorSchedule", cascade="all, delete-orphan", back_populates="doctor"
    )


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="ck_schedule_start_before_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    weekday: Mapped[int]  # 0 = lundi ... 6 = dimanche
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    doctor = relationship("Doctor", back_populates="schedules")