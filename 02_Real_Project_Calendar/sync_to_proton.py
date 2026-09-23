"""
Pushes events.json into Proton Calendar via proton-cli, one calendar per
event type so each type gets its own colour. Re-running this is safe:
proton-cli's import matches events by UID, so it updates existing entries
rather than duplicating them.

Usage:
    uv run python sync_to_proton.py [events.json]
"""

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar, Event

from proton_helper import list_events_chunked

CALENDARS = {
    "LECTURE": {"name": "Timetable - Lecture", "color": "slateblue"},
    "SEMINAR": {"name": "Timetable - Seminar", "color": "carrot"},
    "ONLINE": {"name": "Timetable - Online", "color": "fern"},
}
STATUS_MAP = {"Confirmed": "CONFIRMED", "Tentative": "TENTATIVE", "Cancelled": "CANCELLED"}
UID_SUFFIX = "@mytimetable.worc.ac.uk"

events_path = Path(sys.argv[1] if len(sys.argv) > 1 else "events.json")
events = json.loads(events_path.read_text())

by_type = {}
for e in events:
    by_type.setdefault(e["type"], []).append(e)

unknown = set(by_type) - set(CALENDARS)
if unknown:
    sys.exit(
        f"Event type(s) {unknown} have no calendar mapping - add them to CALENDARS in this script."
    )


def assign_synth_uids(items):
    """The source system reuses one EventIdentity across multiple distinct
    occurrences of what it considers "the same" recurring slot (e.g. the
    same seminar in week 4 and week 12 share a uid). Since events are
    matched 1:1 by uid, that collapses them into a single Proton event and
    silently drops the rest. Disambiguate only the colliding ones by
    appending their start time; anything with a unique EventIdentity keeps
    its plain uid so normal reschedule-updates still update in place
    instead of delete+recreate."""
    counts = Counter(e["uid"] for e in items)
    for e in items:
        base = e["uid"]
        e["_synth_uid"] = base if counts[base] == 1 else f"{base}-{e['start']}"


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

for etype, meta in CALENDARS.items():
    if etype not in by_type:
        continue
    if meta["name"] not in existing:
        print(f"Creating calendar '{meta['name']}'...")
        subprocess.run(
            [
                "proton",
                "calendar",
                "settings",
                "calendars",
                "create",
                "--name",
                meta["name"],
                "--color",
                meta["color"],
                "-y",
            ],
            check=True,
        )
        # New calendars default to a 15m popup + 15m email reminder on every
        # event; drop the email one, keep the 15m popup. Passing --remind
        # replaces the whole default_reminders list, not just appends to it.
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

    items = by_type[etype]
    assign_synth_uids(items)

    cal = Calendar()
    cal.add("prodid", "-//calendar_scrape//mytimetable-sync//EN")
    cal.add("version", "2.0")

    for e in items:
        ev = Event()
        ev.add("uid", f"{e['_synth_uid']}{UID_SUFFIX}")
        ev.add("dtstamp", datetime.now(timezone.utc))
        ev.add("dtstart", datetime.fromisoformat(e["start"]))
        ev.add("dtend", datetime.fromisoformat(e["end"]))
        ev.add("summary", f"{etype.title()}: {e['name'].split(',')[0].strip()}")
        ev.add("description", e.get("description") or "")
        if e.get("location"):
            ev.add("location", e["location"])
        ev.add("status", STATUS_MAP.get(e.get("status"), "CONFIRMED"))
        cal.add_component(ev)

    ics_path = Path(f"timetable_{etype.lower()}.ics")
    ics_path.write_bytes(cal.to_ical())

    print(f"Importing {len(by_type[etype])} {etype} events into '{meta['name']}'...")
    subprocess.run(
        ["proton", "calendar", "events", "import", str(ics_path), "--calendar", meta["name"], "-y"],
        check=True,
    )

# Delete anything that's disappeared from the source timetable (cancelled
# sessions, etc). Only ever touches events we created (uid ends with our
# suffix), scoped to the three calendars this script manages.
current_uids = {f"{e['_synth_uid']}{UID_SUFFIX}" for e in events}

print("Checking for events removed from the source...")
stale = []
for meta in CALENDARS.values():
    live = list_events_chunked(meta["name"], "2026-08-01", "2027-08-31")
    stale.extend(e for e in live if e["uid"].endswith(UID_SUFFIX) and e["uid"] not in current_uids)

deleted = 0
for e in stale:
    print(f"  Deleting '{e['title']}' ({e['start']}) - no longer in the source timetable")
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

print(f"Deleted {deleted}/{len(stale)} stale event(s).")
print("Done.")
