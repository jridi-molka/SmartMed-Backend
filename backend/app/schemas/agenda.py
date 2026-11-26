import datetime as dt
from typing import Literal

from pydantic import BaseModel


class AgendaItemOut(BaseModel):
    id: int
    patient_name: str
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    status: str


class StatusUpdate(BaseModel):
    status: Literal["completed", "no_show"]