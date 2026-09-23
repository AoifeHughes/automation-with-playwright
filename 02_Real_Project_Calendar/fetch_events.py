"""Open mytimetable.worc.ac.uk in a headed browser, wait for you to sign in
to the university account yourself, and dump the visible events to
events.json.

The XHR response at FilterIncludePersonalAndBookings carries the timetable
payload as JSON; we capture it off the network rather than scraping the
Angular UI, then flatten it into one row per event.

Usage:
    uv run python 02_Real_Project_Calendar/fetch_events.py
    uv run python 02_Real_Project_Calendar/fetch_events.py -o my_events.json
"""

import argparse
import json

from playwright.sync_api import Response, sync_playwright

from login_flow import wait_for_user_login

CALENDAR_URL = "https://mytimetable.worc.ac.uk/"
TIMETABLE_URL = (
    "https://mytimetable.worc.ac.uk/timetables"
    "?date=2026-08-31&view=week&searchPanel=true"
    "&datePeriod=all%20year%20(26-27)&all_weeks=true"
)
EVENTS_ENDPOINT = "FilterIncludePersonalAndBookings"


def flatten(payload: dict) -> list[dict]:
    """Pulls every ResourceEvents list out of CategoryEvents/BookingRequests/
    PersonalEvents (whichever are populated) into one flat list."""
    raw_events = []
    for section in ("CategoryEvents", "BookingRequests", "PersonalEvents"):
        results = (payload.get(section) or {}).get("Results", [])
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", default="events.json")
    args = parser.parse_args()

    events_payload: dict = {}

    def on_response(response: Response) -> None:
        if EVENTS_ENDPOINT in response.url:
            try:
                events_payload.update(response.json())
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.on("response", on_response)

        # mytimetable.worc.ac.uk redirects to Microsoft/ADFS for login; the
        # headed browser lands on the Microsoft form, the user fills it in,
        # and we just wait for the URL to come back.
        page.goto(CALENDAR_URL)
        wait_for_user_login(page)

        print("Navigating to timetable view...")
        events_payload.clear()
        page.goto(TIMETABLE_URL, wait_until="networkidle")
        page.wait_for_timeout(4000)  # give the Angular app time to fetch events

        browser.close()

    events = flatten(events_payload)
    with open(args.out, "w") as f:
        json.dump(events, f, indent=2)

    print(f"Saved {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()
