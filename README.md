# Automation with Playwright

A small, hands-on lesson on using
[Playwright](https://playwright.dev/python/) for Python to automate a
browser — from "install it and click around" to a real project that pulls
a school timetable and syncs it into a calendar (run by hand).

## Who this is for

Anyone who can run a terminal and wants to understand, step by step, how a
one-off manual web task becomes a repeatable script.

## How it is laid out

Four lessons, in order. Each lives in its own folder and has its own
`README.md`.

| # | Folder | What you'll get out of it |
|---|--------|---------------------------|
| 00 | [`00_Installing/`](00_Installing/) | Install Playwright + its browser via uv (one shared venv), on macOS/Linux or Windows. |
| 01 | [`01_First_Use/`](01_First_Use/) | Use Playwright's recorder to turn clicks into a script, then replay it. The core loop. |
| 02 | [`02_Real_Project_Calendar/`](02_Real_Project_Calendar/) | A real project: scrape a timetable + assignment due-dates from a logged-in portal and sync both to Proton Calendar. Runs by hand - the launchd weekly job is not included. |
| 03 | [`03_Small_Example_Calendar/`](03_Small_Example_Calendar/) | A compact, single-file version of the lesson-02 idea, to read end-to-end in one sitting. |

Start at **00_Installing** and work down. Lesson 02 is the capstone; if the
full project feels like a lot, lesson 03 is the same concept shrunk down.

## Status — work in progress

This scaffold is **not finished**. The structure and the scripts are in
place, but each lesson README still needs:

- [ ] plain-English "what's happening and why" for each step,
- [] screenshots of the real output (record panel, a synced calendar, …),
- [] any gotchas called out explicitly.

Everything that still needs writing is marked `[TODO: …]` inside the lesson
`README.md`s.

## A note on secrets

No credentials live in this repo. Lesson 02 reads its portal login from
Vaultwarden (via the `bw` CLI) and unlocks it with a macOS Keychain entry -
the scheduled weekly job that used that setup is **not** included in this
repo; run the fetch/sync by hand instead. Lesson 03 prompts for the login on
the command line and keeps nothing.

If you copy these folders into your own machine, re-run the dependency
install (`mac_install.sh`, which runs `uv sync`) and point the config at
your own accounts.

## File map

```
.
├── README.md                     # this file
├── pyproject.toml                # shared deps (playwright, icalendar)
├── .pre-commit-config.yaml       # lint/format hooks (ruff)
├── 00_Installing/                # install Playwright + Chromium (uv sync)
├── 01_First_Use/                 # record + replay a browser script
├── 02_Real_Project_Calendar/     # full timetable/due-dates -> Proton (run by hand)
└── 03_Small_Example_Calendar/    # single-file version of lesson 02
```
