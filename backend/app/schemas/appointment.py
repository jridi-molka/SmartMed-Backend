from datetime import date, time

from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    doctor_id: int
    date: date
    start_time: time


class DoctorSummary(BaseModel):
    id: int
    name: str
    specialty: str


class AppointmentOut(BaseModel):
    id: int
    doctor: DoctorSummary
    date: date
    start_time: time
    end_time: time
    status: str

    model_config = ConfigDict(from_attributes=True)