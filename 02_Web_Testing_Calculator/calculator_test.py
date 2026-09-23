#!/usr/bin/env python3
"""Web-test the lesson-02 calculator by driving it like a human would.

Usage:
    uv run python 02_Web_Testing_Calculator/calculator_test.py
    uv run python 02_Web_Testing_Calculator/calculator_test.py --headless

Opens the static calculator in site/index.html in a real Chromium window
(visible by default; --headless runs with no window), presses the
buttons one at a time, prints every step with a short pause in between
so you can follow along, and checks the display after each scenario.
Exits 0 if every scenario passes, 1 otherwise.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# Resolve the site relative to this script, so the run works from the
# repo root (or anywhere) without a web server.
SITE_URI = (Path(__file__).resolve().parent / "site" / "index.html").as_uri()
STEP_DELAY_MS = 400


def press(page, test_id, label):
    """Click one button, announcing it and pausing so the run is watchable."""
    print(f"==> press {label}")
    page.get_by_test_id(test_id).click()
    page.wait_for_timeout(STEP_DELAY_MS)


def check(page, expected):
    """Read the display and print PASS/FAIL against the expected value."""
    actual = (page.get_by_test_id("display").text_content() or "").strip()
    status = "PASS" if actual == expected else "FAIL"
    print(f"    display: {actual!r} (expected {expected!r}) -> {status}")
    return actual == expected


def main():
    headless = "--headless" in sys.argv
    print(f"==> Opening calculator at {SITE_URI}")

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(SITE_URI)

        # Scenario 1: 2 + 3 = 5
        print("==> Scenario 1: 2 + 3 = 5")
        press(page, "digit-2", "2")
        press(page, "op-plus", "+")
        press(page, "digit-3", "3")
        press(page, "equals", "=")
        results.append(check(page, "5"))

        # Scenario 2: C resets the display to 0
        print("==> Scenario 2: C clears back to 0")
        press(page, "clear", "C")
        results.append(check(page, "0"))

        # Scenario 3: 6 × 7 = 42
        print("==> Scenario 3: 6 × 7 = 42")
        press(page, "digit-6", "6")
        press(page, "op-multiply", "×")
        press(page, "digit-7", "7")
        press(page, "equals", "=")
        results.append(check(page, "42"))

        # Scenario 4: C again
        print("==> Scenario 4: C clears back to 0")
        press(page, "clear", "C")
        results.append(check(page, "0"))

        # Scenario 5: 10 ÷ 4 = 2.5
        print("==> Scenario 5: 10 ÷ 4 = 2.5")
        press(page, "digit-1", "1")
        press(page, "digit-0", "0")
        press(page, "op-divide", "÷")
        press(page, "digit-4", "4")
        press(page, "equals", "=")
        results.append(check(page, "2.5"))

        browser.close()

    passed = sum(results)
    print(f"==> {passed}/{len(results)} scenarios passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
