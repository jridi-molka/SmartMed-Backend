import datetime as dt

from pydantic import BaseModel


class CheckInIn(BaseModel):
    appointment_id: int


class QueueStatusOut(BaseModel):
    queue_entry_id: int
    status: str
    position: int
    patients_before: int
    estimated_wait_minutes: int | None = None
    method: str | None = None
    updated_at: dt.datetime

class QueueEntryOut(BaseModel):
    id: int
    patient_name: str
    appointment_time: dt.time
    status: str
    checked_in_at: dt.datetime
    called_at: dt.datetime | None = None
    started_at: dt.datetime | None = None
    ended_at: dt.datetime | None = None