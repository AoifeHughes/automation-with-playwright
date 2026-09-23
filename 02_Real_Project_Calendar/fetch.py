"""
Run after login.py (uv run python fetch.py). Reuses the saved session - no
password or 2FA involved - and dumps what it can see so we can check what's
actually accessible before doing anything more structured.
"""

import re

from playwright.sync_api import sync_playwright

from config import CALENDAR_URL, STATE_FILE

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=STATE_FILE)
    page = context.new_page()

    page.goto(CALENDAR_URL, wait_until="networkidle")

    print("URL after load:", page.url)
    print("Title:", page.title())

    if re.search(r"login\.microsoftonline\.com|login\.live\.com", page.url):
        print("\nLooks like the session expired - re-run `uv run python login.py`.")
    else:
        page.screenshot(path="page.png", full_page=True)
        text = page.inner_text("body")
        with open("page-text.txt", "w") as f:
            f.write(text)
        print("\nSaved page.png and page-text.txt for inspection.")

    browser.close()
