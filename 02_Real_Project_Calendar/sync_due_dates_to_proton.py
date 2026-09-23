"""
Pushes due_dates.json into a single "Due Dates" Proton calendar. Same
UID-matched import/delete pattern as sync_to_proton.py, so re-running is
safe. Kept separate from the timetable calendars/pyproject flow.

Usage:
    uv run python sync_due_dates_to_proton.py [due_dates.json]
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar, Event

from proton_helper import list_events_chunked

CALENDAR_NAME = "Due Dates"
CALENDAR_COLOR = "strawberry"
UID_SUFFIX = "@worcesterbb.blackboard.com"
# Wide enough to cover the whole 2026-27 academic year - matches the scope
# fetch_due_dates.py queries.
LIST_START, LIST_END = "2026-08-01", "2027-08-31"

due_dates_path = Path(sys.argv[1] if len(sys.argv) > 1 else "due_dates.json")
due_dates = json.loads(due_dates_path.read_text())

calendars_json = json.loads(
    subprocess.run(
        ["proton", "calendar", "settings", "calendars", "list", "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    or "{}"
)
existing = {c["name"]: c["id"] for c in calendars_json.get("calendars", [])}

if CALENDAR_NAME not in existing:
    print(f"Creating calendar '{CALENDAR_NAME}'...")
    subprocess.run(
        [
            "proton",
            "calendar",
            "settings",
            "calendars",
            "create",
            "--name",
            CALENDAR_NAME,
            "--color",
            CALENDAR_COLOR,
            "-y",
        ],
        check=True,
    )
    # Same reminder preference as the timetable calendars: popup only, no email.
    subprocess.run(
        [
            "proton",
            "calendar",
            "settings",
            "calendars",
            "update",
            CALENDAR_NAME,
            "--remind",
            "15m",
            "-y",
        ],
        check=True,
    )

cal = Calendar()
cal.add("prodid", "-//calendar_scrape//blackboard-due-dates//EN")
cal.add("version", "2.0")

for e in due_dates:
    ev = Event()
    ev.add("uid", f"{e['uid']}{UID_SUFFIX}")
    ev.add("dtstamp", datetime.now(timezone.utc))
    due = datetime.fromisoformat(e["due"])
    ev.add("dtstart", due)
    ev.add("dtend", due)
    ev.add("summary", f"Due: {e['title']}")
    ev.add("description", f"Course: {e['course']}\nCourse page: {e['course_url']}")
    ev.add("status", "CONFIRMED")
    cal.add_component(ev)

ics_path = Path("due_dates.ics")
ics_path.write_bytes(cal.to_ical())

print(f"Importing {len(due_dates)} due dates into '{CALENDAR_NAME}'...")
subprocess.run(
    ["proton", "calendar", "events", "import", str(ics_path), "--calendar", CALENDAR_NAME, "-y"],
    check=True,
)

print("Checking for due dates removed from the source...")
current_uids = {f"{e['uid']}{UID_SUFFIX}" for e in due_dates}
live = list_events_chunked(CALENDAR_NAME, LIST_START, LIST_END)
stale = [e for e in live if e["uid"].endswith(UID_SUFFIX) and e["uid"] not in current_uids]

deleted = 0
for e in stale:
    print(f"  Deleting '{e['title']}' ({e['start']}) - no longer in the source")
    ref = f"{e['calendar_id']}/{e['id']}"
    # -y before "--" so it's parsed as a flag; "--" stops flag parsing so a
    # ref that happens to start with "-" (calendar/event IDs are unpadded
    # base64 and can start with anything) isn't mistaken for a flag itself.
    result = subprocess.run(
        ["proton", "calendar", "events", "delete", "-y", "--", ref], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(
            f"    WARNING: delete failed, skipping: {result.stdout.strip() or result.stderr.strip()}"
        )
        continue
    deleted += 1

print(f"Deleted {deleted}/{len(stale)} stale due date(s).")
print("Done.")
