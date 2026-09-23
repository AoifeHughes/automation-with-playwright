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
| 02 | [`02_Real_Project_Calendar/`](02_Real_Project_Calendar/) | A real project: scrape a Worcester timetable and Blackboard assignment due dates from a logged-in portal into two JSON files. Runs by hand. |
| 03 | [`03_Small_Example_Calendar/`](03_Small_Example_Calendar/) | A compact, single-file version of the lesson-02 idea, to read end-to-end in one sitting. |

Start at **00_Installing** and work down. Lesson 02 is the capstone; if the
full project feels like a lot, lesson 03 is the same concept shrunk down.

## File map

```
.
├── README.md                     # this file
├── pyproject.toml                # shared deps (playwright, icalendar)
├── .pre-commit-config.yaml       # lint/format hooks (ruff)
├── 00_Installing/                # install Playwright + Chromium (uv sync)
├── 01_First_Use/                 # record + replay a browser script
├── 02_Real_Project_Calendar/     # full timetable + due-dates -> two JSON files (run by hand)
└── 03_Small_Example_Calendar/    # single-file version of lesson 02
```
