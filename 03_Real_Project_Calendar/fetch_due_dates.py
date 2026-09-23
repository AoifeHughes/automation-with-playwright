"""Open Blackboard Ultra in a headed browser, walk through the third-party
SSO flow, and dump assignment due dates to due_dates.json.

Blackboard's "Calendar -> Due Dates" tab is backed by
/learn/api/v1/calendars/dueDateCalendarItems. Clicking a due date in the
real UI opens a one-time Turnitin LTI launch link, which isn't something
we can save and reuse later; the stable URL we can record is the course
outline page, built from calendarId.

Usage:
    uv run python 03_Real_Project_Calendar/fetch_due_dates.py
    uv run python 03_Real_Project_Calendar/fetch_due_dates.py -o my_due.json
"""

import argparse
import json
import sys

from playwright.sync_api import sync_playwright

from login_flow import wait_for_user_login

CALENDAR_URL = "https://worcesterbb.blackboard.com/ultra/calendar"
BASE = "https://worcesterbb.blackboard.com"
DUE_DATES_ENDPOINT = "/learn/api/v1/calendars/dueDateCalendarItems"


def start_sso(page) -> None:
    """Blackboard doesn't redirect to Microsoft immediately - it shows its
    own login form first, with SSO tucked under a 'Sign in with a third-party
    account' accordion. Drive that, then hand off to wait_for_user_login."""
    page.locator('button:has-text("OK")').first.click(timeout=5000)  # cookie consent
    page.wait_for_timeout(500)
    page.locator("text=Sign in with a third-party account").first.click(timeout=5000)
    page.wait_for_timeout(500)
    page.locator("text=University SSO Login").first.click(timeout=5000)
    page.wait_for_load_state("networkidle", timeout=30000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", default="due_dates.json")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(CALENDAR_URL, wait_until="networkidle")
        start_sso(page)
        wait_for_user_login(page)

        print("Fetching due dates...")
        raw: dict = {}
        offset, limit = 0, 50
        while True:
            path = (
                f"{DUE_DATES_ENDPOINT}?date=2000-01-01T00:00:00.000Z"
                f"&date_compare=greaterOrEqual&includeCount=true&limit={limit}&offset={offset}"
            )
            resp = context.request.get(BASE + path, headers={"Accept": "application/json"})
            if resp.status != 200:
                sys.exit(f"dueDateCalendarItems failed: {resp.status} {resp.text()[:300]}")
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
            "course_url": f"{BASE}/ultra/{e['calendarId']}/outline",
            "type": (e.get("dynamicCalendarItemProps") or {}).get("eventType"),
        }
        for e in sorted(raw.values(), key=lambda e: e["startDate"])
    ]

    with open(args.out, "w") as f:
        json.dump(due_dates, f, indent=2)

    print(f"Saved {len(due_dates)} due dates to {args.out}")


if __name__ == "__main__":
    main()
