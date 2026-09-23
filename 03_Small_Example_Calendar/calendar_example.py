#!/usr/bin/env python3
"""Slowed-down, watchable version of calendar/calendar_scrape/fetch_events.py.

Reads the mytimetable.worc.ac.uk login straight off the command line, then
drives a visible browser through the Microsoft/ADFS login and onto the
timetable. It pauses 10 seconds before every step so you can see what's
happening, saves the scraped events to JSON, and then leaves the browser
open until you close the window yourself.

Usage:
    python calendar_example/calendar_example.py [-o events.json]

You'll be prompted for the mytimetable username, password and (if the site
asks for it) the TOTP code. Nothing is stored - just type it in when asked.

Needs playwright installed (see ../.., which creates the shared venv).
"""

import argparse
import getpass
import json

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

CALENDAR_URL = "https://mytimetable.worc.ac.uk/"
TIMETABLE_URL = (
    "https://mytimetable.worc.ac.uk/timetables"
    "?date=2026-08-31&view=week&searchPanel=true"
    "&datePeriod=all%20year%20(26-27)&all_weeks=true"
)
EVENTS_ENDPOINT = "FilterIncludePersonalAndBookings"

STEP_DELAY_MS = 10_000


# --- Prompting -------------------------------------------------------------


def prompt_username():
    return input("mytimetable username: ").strip()


def prompt_password():
    # Masked, like a normal password field.
    return getpass.getpass("mytimetable password: ")


# --- Browser helpers -------------------------------------------------------


def step(page, message):
    """Wait 10 seconds, then announce the next step."""
    print(f"  (waiting {STEP_DELAY_MS // 1000}s)")
    page.wait_for_timeout(STEP_DELAY_MS)
    print(f"==> {message}")


def try_fill(page, selectors, value, timeout=8000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.fill(value)
            return True
        except PWTimeout:
            continue
    return False


def try_click(page, selectors, timeout=4000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            return True
        except PWTimeout:
            continue
    return False


# --- Scraping --------------------------------------------------------------


def flatten(payload):
    """Pulls every ResourceEvents list out of the timetable API response into
    one flat list of simple dicts."""
    raw_events = []
    for section in ("CategoryEvents", "BookingRequests", "PersonalEvents"):
        for entry in (payload.get(section) or {}).get("Results", []):
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


# --- Main ------------------------------------------------------------------

parser = argparse.ArgumentParser(
    description="Prompt for a mytimetable login and scrape the current timetable."
)
parser.add_argument("-o", "--out", default="events.json")
args = parser.parse_args()

print("==> Please enter your mytimetable credentials (typed privately).")
username = prompt_username()
password = prompt_password()
print(f"    Logged in as '{username}' (TOTP requested only if the site asks).")

events_payload = {}


def on_response(response):
    if EVENTS_ENDPOINT in response.url:
        try:
            events_payload.update(response.json())
        except Exception:
            pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.on("response", on_response)

    print(f"==> Opening {CALENDAR_URL}")
    page.goto(CALENDAR_URL)

    step(page, "Clicking 'Log in'")
    try_click(
        page,
        [
            "button:has-text('Log in')",
            "a:has-text('Log in')",
            "a:has-text('Login')",
            "button:has-text('Sign in')",
        ],
        timeout=6000,
    )

    step(page, "Filling in username")
    try_fill(page, ["input[name='loginfmt']", "#userNameInput", "input[type='email']"], username)
    try_click(page, ["#idSIButton9", "#submitButton", "button:has-text('Next')"])

    step(page, "Filling in password")
    try_fill(page, ["input[name='passwd']", "#passwordInput", "input[type='password']"], password)
    try_click(page, ["#idSIButton9", "#submitButton", "button:has-text('Sign in')"])

    # The code is only valid for ~30s, so ask for it here (after the pause)
    # rather than up front - and only if the site actually shows a TOTP field.
    try:
        page.locator("input[autocomplete='one-time-code']").first.wait_for(
            state="visible", timeout=5000
        )
        totp = prompt_password()
        step(page, "Filling in TOTP code")
        try_fill(
            page,
            ["input[name='otc']", "#idTxtBx_SAOTCC_OTC", "input[autocomplete='one-time-code']"],
            totp,
            timeout=6000,
        )
        try_click(page, ["#idSubmit_SAOTCC_Continue", "#idSIButton9", "button:has-text('Verify')"])
    except PWTimeout:
        pass

    # Microsoft sometimes inserts an "Improve your sign-ins" interstitial
    # here (nagging you to set up the Authenticator app) before the "Stay
    # signed in?" prompt. It's not always shown, so this is a no-op when
    # it isn't.
    step(page, "Skipping any 'Improve your sign-ins' prompt")
    try_click(page, ["a:has-text('Skip for now')"], timeout=3000)

    step(page, "Answering 'Stay signed in?'")
    try_click(page, ["#idSIButton9", "button:has-text('Yes')"], timeout=5000)
    page.wait_for_load_state("networkidle")

    step(page, "Opening the timetable")
    events_payload.clear()
    page.goto(TIMETABLE_URL, wait_until="networkidle")

    step(page, "Saving events")
    events = flatten(events_payload)
    with open(args.out, "w") as f:
        json.dump(events, f, indent=2)
    print(f"    Saved {len(events)} events to {args.out}")

    print("==> Done. Close the browser window to exit.")
    page.wait_for_event("close", timeout=0)
    browser.close()
