from datetime import datetime
from zoneinfo import ZoneInfo

CABINET_TZ = ZoneInfo("Africa/Tunis")


def now_local() -> datetime:
    """Heure actuelle du cabinet, sans fuseau (comme en base)."""
    return datetime.now(CABINET_TZ).replace(tzinfo=None)