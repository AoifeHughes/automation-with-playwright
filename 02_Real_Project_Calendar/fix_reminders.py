"""
One-off fix: new Proton calendars default to a 15-min popup + 15-min email
reminder on every event. This drops the email one and keeps the 15-min
popup, for the three timetable calendars already created. Reminders are a
calendar-level default here (we never set a per-event alarm on import), so
this affects every event already in them.

Usage:
    uv run python fix_reminders.py
"""

import subprocess

from sync_to_proton import CALENDARS

for meta in CALENDARS.values():
    print(f"Setting popup-only reminder on '{meta['name']}'...")
    subprocess.run(
        [
            "proton",
            "calendar",
            "settings",
            "calendars",
            "update",
            meta["name"],
            "--remind",
            "15m",
            "-y",
        ],
        check=True,
    )

print("Done.")
