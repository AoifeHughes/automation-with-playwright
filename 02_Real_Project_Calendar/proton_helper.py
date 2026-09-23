"""Shared helpers for talking to proton-cli from the sync scripts."""

import json
import subprocess
from datetime import date

# `proton calendar events list` rejects windows above roughly a few months
# ("Time window is too big"), so wide ranges have to be walked in chunks.
CHUNK_DAYS = 31


def _add_days(d: date, days: int) -> date:
    from datetime import timedelta

    return d + timedelta(days=days)


def list_events_chunked(calendar_name: str, start: str, end: str) -> list[dict]:
    start_d, end_d = date.fromisoformat(start), date.fromisoformat(end)
    events, cursor = [], start_d
    while cursor < end_d:
        chunk_end = min(_add_days(cursor, CHUNK_DAYS), end_d)
        result = subprocess.run(
            [
                "proton",
                "calendar",
                "events",
                "list",
                "--calendar",
                calendar_name,
                "--start",
                cursor.isoformat(),
                "--end",
                chunk_end.isoformat(),
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        events.extend(json.loads(result.stdout).get("events", []))
        cursor = _add_days(chunk_end, 1)
    return events
