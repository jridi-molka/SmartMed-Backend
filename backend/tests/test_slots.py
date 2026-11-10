from datetime import date, datetime, time

from app.services.slot_service import generate_slots

DAY = date(2026, 11, 16)  # un lundi
PAST = datetime(2026, 11, 1, 8, 0)  # "maintenant" très tôt : rien n'est passé


def test_three_slots_in_one_hour():
    slots = generate_slots([(time(9, 0), time(10, 0))], 20, set(), PAST, DAY)
    assert [s["start_time"] for s in slots] == ["09:00", "09:20", "09:40"]


def test_booked_slot_unavailable():
    slots = generate_slots([(time(9, 0), time(10, 0))], 20, {time(9, 20)}, PAST, DAY)
    assert [s["available"] for s in slots] == [True, False, True]


def test_past_slot_unavailable():
    now = datetime(2026, 11, 16, 9, 30)
    slots = generate_slots([(time(9, 0), time(10, 0))], 20, set(), now, DAY)
    assert [s["available"] for s in slots] == [False, False, True]


def test_range_not_exact():
    slots = generate_slots([(time(9, 0), time(9, 50))], 20, set(), PAST, DAY)
    assert len(slots) == 2


def test_two_ranges_in_a_day():
    ranges = [(time(9, 0), time(10, 0)), (time(14, 0), time(15, 0))]
    slots = generate_slots(ranges, 20, set(), PAST, DAY)
    assert len(slots) == 6