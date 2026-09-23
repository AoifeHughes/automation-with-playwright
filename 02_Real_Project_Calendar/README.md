# Lesson 02 — Real project: timetable & due dates → Proton Calendar

## Objective

Put the record-and-replay idea from lessons 00–01 to work on something
real. This folder contains a working project that, once a week:

1. logs into a portal that needs a Microsoft/ADFS sign-in,
2. reads your timetable **and** your assignment due dates,
3. syncs both into Proton Calendar — creating calendars, updating changed
   events by UID, and deleting events that have gone.

It's the natural "lesson 01, but for real" capstone. Lesson 03 is the same
idea shrunk down to a single file if you'd rather read the whole thing in
one sitting.

## What the pieces do

The project is split so each concern is small and readable:

| File | What it does |
|------|--------------|
| `config.py` | Site URLs, Vaultwarden item/email, session-state file name. |
| `bw_helper.py` | Wraps the `bw` CLI: unlock the vault, read a field, list matches. |
| `secrets_helper.py` | Reads the Vaultwarden master password from the macOS Keychain. |
| `login_flow.py` | Shared Playwright logic that drives the Microsoft/ADFS login form. |
| `login_auto.py` | Interactive login *test* — opens a visible browser and pauses. Debugging aid only. |
| `fetch_events.py` | Logs in, loads the timetable, writes `events.json`. |
| `sync_to_proton.py` | Pushes `events.json` into Proton: creates the 3 calendars, imports/updates, deletes stale ones. |
| `fix_reminders.py` | One-off script (already run) that sets the calendars to popup-only reminders. |
| `fetch_due_dates.py`, `sync_due_dates_to_proton.py` | Same pattern as the timetable, for assignment due dates. |
| `fetch_blackboard_files.py` | Downloads file attachments from Blackboard courses. |
| `crawl_blackboard.py` | Auto-discourses every enrolled course and downloads *every* file, mirroring Blackboard's structure. Safe to rerun (tracked by `blackboard_manifest.json`). |
| `weekly_sync.sh` | Manual one-shot: fetch, then sync. (The launchd weekly job is not part of this repo.) |
| `login.py`, `fetch.py`, `keychain_test.py`, `explore_events.py` | Earlier prototypes/exploration, kept for reference. |
| deps | Live in the repo-root `pyproject.toml` - run `uv sync` once at the repo root. |

Sample data you can open and inspect: `events.json`, `due_dates.json`,
`due_dates.ics`, `timetable_*.ics`. These are real, but only your own data
shapes — good reference for what the scripts produce.

## The full operational guide

The detailed how-it-actually-runs guide - secrets handling and the Keychain
entry - lives in
[`PROJECT.md`](PROJECT.md). Read that after you've got the shape of the
project; it's the "operating manual" rather than the lesson.

## Steps

```bash
# 1. install dependencies (Playwright + Chromium land here)
uv sync

# 2. log in once and see the timetable captured to JSON
uv run python fetch_events.py

# 3. push it into Proton Calendar
uv run python sync_to_proton.py
```

(Or run steps 2 + 3 together by hand via `weekly_sync.sh` - it's a manual
one-shot now, not scheduled.)

## Why this lesson matters

It shows everything a real Playwright automation has to solve that the
`example.com` demo doesn't:

- **Authentication** you can't just `page.goto()` into — a multi-step
  Microsoft login, TOTP, interstitial prompts.
- **Reading data the site never renders plainly** — catching the XHR
  response that carries the timetable JSON.
- **Secrets** kept out of the code (Vaultwarden + Keychain), so nothing
  sensitive is hardcoded.
- **Idempotency** — matching by UID so edits and cancellations propagate
  instead of piling up duplicates.

---

> [TODO] Fill in with:
> - a screenshot of the logged-in portal / timetable page,
> - a screenshot of `events.json` (or `due_dates.json`) open,
> - a screenshot of Proton Calendar showing the synced calendars,
> - a plain-English walkthrough of `login_flow.py` and the "catch the XHR
>   response" trick in `fetch_events.py`,
> - a short explanation of how secrets get from Vaultwarden/Keychain into
>   the run, without pasting any secrets.
