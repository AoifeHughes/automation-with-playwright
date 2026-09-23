"""
Run once (uv run python login.py) to authenticate manually and save the
session. A real Chromium window opens - log in to the Microsoft account
yourself, including whatever 2FA prompt you get. Once the calendar page
has loaded, come back to the terminal and press Enter to save the session.

This sidesteps password/2FA automation entirely: after this runs once,
fetch.py reuses the saved cookies until they expire.
"""

from playwright.sync_api import sync_playwright

from config import CALENDAR_URL, STATE_FILE

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(CALENDAR_URL)

    input("\nLog in in the browser window, then press Enter here once you see the calendar...\n")

    context.storage_state(path=STATE_FILE)
    print(f"Saved session to {STATE_FILE}")

    browser.close()
