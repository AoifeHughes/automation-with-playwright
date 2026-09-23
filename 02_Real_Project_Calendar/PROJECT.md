# Worcester calendar scrape

Pulls your Worcester timetable (mytimetable.worc.ac.uk) and your
Blackboard assignment due dates into two JSON files, both fetched by hand
with a headed browser. Prompt-driven login: the scripts open a browser,
print a prompt, and wait for you to sign in. Nothing in this folder talks
to anything outside Playwright + the two university sites.

> NOTE - this is a lesson repo. There's no `launchd` (or any other) job
> here; both scripts are run by hand with `uv run python`. The login,
> XHR-capture and pagination logic is what's being demonstrated.

## Requirements

- **uv** (Python project/dependency manager) - `brew install uv`
- **Python 3.11+** - managed automatically by uv, no separate install needed
- **Playwright + Chromium** - installed into the shared repo `.venv` by
  `uv sync` (run once from the repo root); Chromium itself via
  `uv run playwright install chromium`

Deps come from the repo root `pyproject.toml`/`uv.lock` (run `uv sync` once
at the repo root - see `../..`); there is no per-folder `pyproject.toml`
here.

That's the full list - no env vars, no external services, no per-folder
config. Both scripts just open a headed browser and wait for you to sign
in.

## Files

| File | Purpose |
|---|---|
| `fetch_events.py` | Opens `mytimetable.worc.ac.uk` in a headed Chromium, waits for the Microsoft/ADFS login to complete, navigates to the timetable view, hooks `page.on("response", ...)` to capture the `FilterIncludePersonalAndBookings` XHR, flattens the payload (CategoryEvents / BookingRequests / PersonalEvents) into one row per session, writes `events.json`. |
| `fetch_due_dates.py` | Opens Worcester Blackboard Ultra, dismisses the cookie consent, opens the "Sign in with a third-party account" accordion, clicks "University SSO Login", waits for the ADFS login to complete, then paginates `/learn/api/v1/calendars/dueDateCalendarItems` (limit=50, offset loops until a short page) and writes `due_dates.json`. |
| `login_flow.py` | `wait_for_user_login(page)` helper shared by both fetchers. Prints the prompt, polls `page.url` until it leaves `login.microsoftonline.com` / `login.live.com`, with a ~30s polling window and an `input()` fallback if an SSO bounce confuses the host check. |
| `README.md` | The lesson scaffold - what each script does at a high level, the walkthrough screenshots. |
| `screenshots/` | The walkthrough images embedded in the README. |

## Running it

Neither script is scheduled here - run them by hand whenever you want a
fresh snapshot:

    uv run python 02_Real_Project_Calendar/fetch_events.py
    uv run python 02_Real_Project_Calendar/fetch_due_dates.py

Both are headed (`chromium.launch(headless=False)`). Both call
`wait_for_user_login(page)` after the initial navigation, which prints a
prompt and blocks until the URL leaves the Microsoft/ADFS hosts. If an
SSO bounce confuses the host check you'll get a fallback prompt after
~30s asking you to press Enter once you're done in the browser.

Both scripts take an optional `-o / --out` to redirect the JSON output
somewhere other than the cwd.

### Outputs

- `fetch_events.py` writes `events.json` (default; override with
  `-o /path/to/file.json`) - one row per session, fields `uid`, `name`,
  `description`, `type`, `start`, `end`, `location`, `status`,
  `week_label`. Order is whatever the timetable hands back.
- `fetch_due_dates.py` writes `due_dates.json` (default; override with
  `-o /path/to/file.json`) - one row per assignment, fields `uid`,
  `title`, `due`, `course`, `course_url`, `type`. Sorted ascending by
  `due`.

Both files are gitignored - they're fresh data on every run, not source.

## Hardcoded values

A few things are baked into the scripts; revisit them when the new
academic year is published:

- `TIMETABLE_URL` in `fetch_events.py` is pinned to the 2026-27 academic
  year (`datePeriod=all year (26-27)`, `all_weeks=true`,
  `date=2026-08-31`). Update both the `date` and the `datePeriod` query
  params when the new year's timetable goes live.
- `fetch_due_dates.py` paginates from `2000-01-01T00:00:00.000Z`
  forwards, which captures everything Blackboard still has - no need to
  bump this each year.
- The Blackboard third-party SSO locator strings (`"Sign in with a
  third-party account"`, `"University SSO Login"`) are matched by visible
  text, so a Blackboard UI rename will need the script updated.
