# Lesson 03 — Small example: a real scrape, in one file

## Objective

Put lessons 00–01 together into a compact, single-file program that does the
same kind of thing as the lesson-02 project, but readable in one sitting: it
logs into `mytimetable.worc.ac.uk`, waits for the timetable API to return, and
saves what it finds to JSON.

## What it does

1. Prompts you, on the command line, for your mytimetable **username**,
   **password** and (only if the site asks for it) **TOTP code**. Nothing is
   stored - you type it in each run.
2. Opens a real Chromium browser and drives the Microsoft/ADFS login.
3. Pauses 10 seconds before each step so you can watch what happens, and
   catches the hidden API response that carries the timetable.
4. Writes the events to `events.json`.

See `calendar_example.py` for the whole thing.

## Files in this lesson

| File | Purpose |
|------|---------|
| `calendar_example.py` | The whole example - prompt, login, scrape, save. |
| `run_mac_example.sh` | One script to set the stage and run `calendar_example.py` against the shared venv. |

## Before you start

Activate the shared virtualenv (once per terminal session):

```bash
source ../.venv/bin/activate
```

## Steps

```bash
./run_mac_example.sh
```

You'll be prompted for the login, then watched the browser do the work.
Alternatively run it directly:

```bash
python calendar_example.py -o my_timetable.json
```

The events are saved to `events.json` (or the path you pass with `-o`).

## Why this lesson matters

It's the lesson-02 project shrunk down: no scheduled job, no secrets files,
no multi-file split. It's meant to be read top to bottom once, then changed -
try swapping the URL, adding a wait, or printing the events as you scrape.
That's the point of the whole thing.
