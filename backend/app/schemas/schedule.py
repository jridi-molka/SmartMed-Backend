from datetime import time

from pydantic import BaseModel, Field, field_serializer, model_validator


class ScheduleSlotIn(BaseModel):
    """Une plage de travail : un jour de la semaine, une heure de début et de fin."""

    weekday: int = Field(ge=0, le=6)  # 0 = lundi ... 6 = dimanche
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def start_before_end(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time doit être avant end_time")
        return self


class ScheduleIn(BaseModel):
    """Toute la semaine d'un coup : la nouvelle liste remplace l'ancienne."""

    days: list[ScheduleSlotIn] = Field(max_length=24)

    @model_validator(mode="after")
    def no_overlap(self):
        by_day: dict[int, list[tuple[time, time]]] = {}
        for slot in self.days:
            by_day.setdefault(slot.weekday, []).append((slot.start_time, slot.end_time))
        for ranges in by_day.values():
            ranges.sort()
            for (_, end1), (start2, _) in zip(ranges, ranges[1:]):
                if start2 < end1:
                    raise ValueError("Deux plages se chevauchent le même jour")
        return self


class ScheduleSlotOut(BaseModel):
    weekday: int
    start_time: time
    end_time: time

    @field_serializer("start_time", "end_time")
    def _as_hh_mm(self, value: time) -> str:
        return value.strftime("%H:%M")


class ScheduleOut(BaseModel):
    days: list[ScheduleSlotOut]