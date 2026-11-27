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