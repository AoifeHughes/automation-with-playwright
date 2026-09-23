"""
Logs in via Vaultwarden creds, loads the requested timetable view, and saves
all timetable events to events.json.

Usage:
    uv run python fetch_events.py [vault-master-password]

If the password is omitted, it's read from Keychain instead (see
secrets_helper.py) - that's what the weekly automated run relies on.
"""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

import bw_helper
import secrets_helper
from config import BITWARDEN_EMAIL, CALENDAR_URL, STATE_FILE, VAULT_ITEM_NAME
from login_flow import perform_login

TIMETABLE_URL = (
    "https://mytimetable.worc.ac.uk/timetables"
    "?date=2026-08-31&view=week&searchPanel=true"
    "&datePeriod=all%20year%20(26-27)&all_weeks=true"
)
EVENTS_ENDPOINT = "FilterIncludePersonalAndBookings"

parser = argparse.ArgumentParser()
parser.add_argument("master_password", nargs="?", default=None)
parser.add_argument("--item", default=VAULT_ITEM_NAME)
parser.add_argument("--email", default=BITWARDEN_EMAIL)
parser.add_argument("-o", "--out", default="events.json")
args = parser.parse_args()

master_password = args.master_password or secrets_helper.get_master_password()

print("Unlocking Vaultwarden...")
session = bw_helper.get_session(args.email, master_password)
username = bw_helper.get_field(session, args.item, "username")
password = bw_helper.get_field(session, args.item, "password")
totp = bw_helper.get_field(session, args.item, "totp")
if not username or not password:
    sys.exit(f"Couldn't get a username/password from vault item '{args.item}'.")

events_payload = {}


def on_response(response):
    if EVENTS_ENDPOINT in response.url:
        try:
            events_payload.update(response.json())
        except Exception:
            pass


def flatten(payload) -> list[dict]:
    """Pulls every ResourceEvents list out of CategoryEvents/BookingRequests/
    PersonalEvents (whichever are populated) into one flat list."""
    raw_events = []
    for section in ("CategoryEvents", "BookingRequests", "PersonalEvents"):
        results = (payload.get(section) or {}).get("Results", [])
        # CategoryEvents entries can themselves nest Categories -> Results too,
        # but for a personal timetable the events live directly under Results.
        for entry in results:
            raw_events.extend(entry.get("ResourceEvents", []))

    cleaned = []
    for e in raw_events:
        location = next(
            (p["Value"] for p in e.get("ExtraProperties", []) if p.get("Name") == "Location Name"),
            e.get("Location") or None,
        )
        cleaned.append(
            {
                "uid": e.get("EventIdentity"),
                "name": e.get("Name"),
                "description": e.get("Description"),
                "type": e.get("EventType"),
                "start": e.get("StartDateTime"),
                "end": e.get("EndDateTime"),
                "location": location,
                "status": e.get("Status"),
                "week_label": e.get("WeekLabels"),
            }
        )
    return cleaned


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.on("response", on_response)

    print("Logging in...")
    page.goto(CALENDAR_URL)
    perform_login(page, username, password, totp)
    page.wait_for_load_state("networkidle")

    context.storage_state(path=STATE_FILE)

    print("Navigating to timetable view...")
    events_payload.clear()
    page.goto(TIMETABLE_URL, wait_until="networkidle")
    page.wait_for_timeout(4000)  # give the Angular app time to fetch events

    browser.close()

events = flatten(events_payload)
with open(args.out, "w") as f:
    json.dump(events, f, indent=2)

print(f"Saved {len(events)} events to {args.out}")
