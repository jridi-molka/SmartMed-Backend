from datetime import date

from pydantic import BaseModel


class SlotOut(BaseModel):
    start_time: str
    end_time: str
    available: bool


class SlotsOut(BaseModel):
    date: date
    doctor_id: int
    slots: list[SlotOut]