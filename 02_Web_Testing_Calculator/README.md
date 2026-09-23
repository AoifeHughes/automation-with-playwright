# Lesson 02 — Web testing: driving a calculator with Playwright

## Objective

Turn Playwright into a plain **web-testing** tool: a script that opens a
small static calculator site, presses its buttons the way a person would,
and checks what the display shows after each step — printing every action
as it goes, so a headed run is something you can actually watch.

## What you'll learn

- Playwright as a web-testing tool, with no test runner in the way: one
  script, one browser, plain prints and per-scenario PASS/FAIL checks.
- Driving a local static site over a `file://` URL — no web server needed.
- Locating elements with stable `data-testid` attributes
  (`page.get_by_test_id(...)`), so the script survives CSS changes.
- Printing each step and pausing a little between them, so a headed run
  is readable rather than a blur.

## Files in this lesson

| File | Purpose |
|------|---------|
| `site/index.html` | The calculator page: one display, 16 buttons, a little inline CSS. |
| `site/calculator.js` | The calculator's state machine, wired to the buttons by `data-testid`. |
| `calculator_test.py` | The Playwright script: open the site, press the buttons, check the display. |

## Before you start

Lesson 00 already created the shared virtualenv and installed Chromium.
If you ever need to reinstall the browser:

```bash
uv run playwright install chromium
```

## Running it

From the repo root:

```bash
uv run python 02_Web_Testing_Calculator/calculator_test.py
```

A visible Chromium window opens, the calculator loads, and the script
presses the buttons one at a time — you can watch it work. To run without
a window (in CI, or just quieter):

```bash
uv run python 02_Web_Testing_Calculator/calculator_test.py --headless
```

It runs five scenarios — `2 + 3 =`, clear, `6 × 7 =`, clear, `10 ÷ 4 =` —
and prints PASS/FAIL after each one. Sample output:

```text
==> Opening calculator at file:///…/02_Web_Testing_Calculator/site/index.html
==> Scenario 1: 2 + 3 = 5
==> press 2
==> press +
==> press 3
==> press =
    display: '5' (expected '5') -> PASS
==> Scenario 2: C clears back to 0
==> press C
    display: '0' (expected '0') -> PASS
...
==> Scenario 5: 10 ÷ 4 = 2.5
==> press 1
==> press 0
==> press ÷
==> press 4
==> press =
    display: '2.5' (expected '2.5') -> PASS
==> 5/5 scenarios passed
```

The exit code is 0 if every scenario passes, 1 if any fails — that's what
a CI system would check.

## Notes

- **No server needed.** The site is opened with a `file://` URL built from
  the script's own location, so a static folder is all it takes, and the
  command runs from the repo root without `cd`-ing anywhere.
- **`--headless` for CI.** The same script runs identically with no
  window; everything is printed either way.
- **Why `data-testid`?** Locators based on class names or layout break the
  moment the page is restyled. A dedicated test id exists only to be
  grabbed by a test, so `page.get_by_test_id("op-plus")` keeps working
  even if the button moves or is reskinned.
