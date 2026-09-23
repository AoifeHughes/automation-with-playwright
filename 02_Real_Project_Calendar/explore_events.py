"""
Exploration pass: logs in, jumps to the requested timetable view, and dumps
every JSON API response the Angular app makes while it loads - so we can
find which one actually holds the event data, before writing a script that
extracts just that into events.json.

Usage:
    uv run python explore_events.py <vault-master-password>
"""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

import bw_helper
from config import BITWARDEN_EMAIL, CALENDAR_URL, VAULT_ITEM_NAME
from login_flow import perform_login

TIMETABLE_URL = (
    "https://mytimetable.worc.ac.uk/timetables"
    "?date=2026-08-31&view=week&searchPanel=true"
    "&datePeriod=all%20year%20(26-27)&all_weeks=true"
)

parser = argparse.ArgumentParser()
parser.add_argument("master_password")
parser.add_argument("--item", default=VAULT_ITEM_NAME)
parser.add_argument("--email", default=BITWARDEN_EMAIL)
args = parser.parse_args()

print("Unlocking Vaultwarden...")
session = bw_helper.get_session(args.email, args.master_password)
username = bw_helper.get_field(session, args.item, "username")
password = bw_helper.get_field(session, args.item, "password")
totp = bw_helper.get_field(session, args.item, "totp")
if not username or not password:
    sys.exit(f"Couldn't get a username/password from vault item '{args.item}'.")

captured = []


def on_response(response):
    ctype = response.headers.get("content-type", "")
    if "json" not in ctype:
        return
    try:
        body = response.json()
    except Exception:
        return
    captured.append({"url": response.url, "body": body})


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.on("response", on_response)

    print("Logging in...")
    page.goto(CALENDAR_URL)
    perform_login(page, username, password, totp)
    page.wait_for_load_state("networkidle")

    print("Navigating to timetable view...")
    captured.clear()  # drop login-time noise, keep only timetable-related calls
    page.goto(TIMETABLE_URL, wait_until="networkidle")
    page.wait_for_timeout(4000)  # give the Angular app time to fetch events

    print(f"\nCaptured {len(captured)} JSON responses:")
    for c in captured:
        size = len(json.dumps(c["body"]))
        print(f"  {c['url']}  ({size} bytes)")

    with open("captured_responses.json", "w") as f:
        json.dump(captured, f, indent=2)

    browser.close()

print("\nSaved raw responses to captured_responses.json for inspection.")
