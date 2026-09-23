"""
Logs into Blackboard Ultra (worcesterbb.blackboard.com) via the same
Vaultwarden login used for mytimetable.worc.ac.uk, and saves every
assignment due date to due_dates.json.

The API backing the Calendar's "Due Dates" tab (dueDateCalendarItems)
doesn't return a direct assignment URL - clicking a due date in the real
UI opens a fresh, single-use Turnitin LTI launch link each time, which
isn't something you can save and reuse later. What IS stable is the link
to the course's Blackboard page, built from the item's calendarId - good
enough to get you to the right place and find the assignment from there.

Usage:
    uv run python fetch_due_dates.py [vault-master-password]
"""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

import bw_helper
import secrets_helper
from blackboard_login import start_sso
from config import BITWARDEN_EMAIL, VAULT_ITEM_NAME
from login_flow import perform_login

CALENDAR_URL = "https://worcesterbb.blackboard.com/ultra/calendar"
DUE_DATES_ENDPOINT = "/learn/api/v1/calendars/dueDateCalendarItems"

parser = argparse.ArgumentParser()
parser.add_argument("master_password", nargs="?", default=None)
parser.add_argument("--item", default=VAULT_ITEM_NAME)
parser.add_argument("--email", default=BITWARDEN_EMAIL)
parser.add_argument("-o", "--out", default="due_dates.json")
args = parser.parse_args()

master_password = args.master_password or secrets_helper.get_master_password()

print("Unlocking Vaultwarden...")
session = bw_helper.get_session(args.email, master_password)
username = bw_helper.get_field(session, args.item, "username")
password = bw_helper.get_field(session, args.item, "password")
totp = bw_helper.get_field(session, args.item, "totp")
if not username or not password:
    sys.exit(f"Couldn't get a username/password from vault item '{args.item}'.")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    print("Logging in...")
    page.goto(CALENDAR_URL, wait_until="networkidle")
    start_sso(page)
    perform_login(page, username, password, totp)
    page.wait_for_load_state("networkidle")

    print("Fetching due dates...")
    base = "https://worcesterbb.blackboard.com"
    raw = {}
    offset, limit = 0, 50
    while True:
        path = (
            f"{DUE_DATES_ENDPOINT}?date=2000-01-01T00:00:00.000Z"
            f"&date_compare=greaterOrEqual&includeCount=true&limit={limit}&offset={offset}"
        )
        resp = context.request.get(base + path, headers={"Accept": "application/json"})
        resp.status == 200 or sys.exit(
            f"dueDateCalendarItems failed: {resp.status} {resp.text()[:300]}"
        )
        results = resp.json().get("results", [])
        for item in results:
            raw[item["itemSourceId"]] = item
        if len(results) < limit:
            break
        offset += limit

    browser.close()

due_dates = [
    {
        "uid": e["itemSourceId"],
        "title": e["title"],
        "due": e["startDate"],
        "course": (e.get("calendarNameLocalizable") or {}).get("rawValue"),
        "course_url": f"https://worcesterbb.blackboard.com/ultra//{e['calendarId']}/outline",
        "type": (e.get("dynamicCalendarItemProps") or {}).get("eventType"),
    }
    for e in sorted(raw.values(), key=lambda e: e["startDate"])
]

with open(args.out, "w") as f:
    json.dump(due_dates, f, indent=2)

print(f"Saved {len(due_dates)} due dates to {args.out}")
