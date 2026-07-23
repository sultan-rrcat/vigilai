from datetime import datetime, timezone


def to_iso_z(dt: datetime) -> str:
    """Serialize a datetime to a JS-parseable ISO-8601 UTC string.

    Handles both naive datetimes (assumed UTC, e.g. from datetime.utcnow())
    and timezone-aware datetimes (e.g. from a DateTime(timezone=True) column).

    Naively appending "Z" to an already-offset-aware isoformat() string
    produces an invalid double-timezone string like "2025-03-23T10:00:01+00:00Z",
    which JavaScript's Date parser rejects (renders as Invalid Date in the UI).
    This normalizes to a naive UTC datetime first so the output is always a
    single, unambiguous "...Z" suffixed string.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat() + "Z"