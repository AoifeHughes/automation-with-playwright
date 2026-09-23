# Lesson 01 — First use: record and replay

## Objective

Turn a handful of real mouse clicks and key presses into a Python script —
with **no writing yet** — then replay that script to reproduce the same
actions automatically. This record → replay loop is the heart of what
Playwright lets you do.

## Files in this lesson

| File | Purpose |
|------|---------|
| `record.py` | Launches Playwright's recorder: it opens a browser + an "Inspector" panel that writes Python as you act. |
| `replay.py` | Replays a recorded script against a fresh browser. |
| `recorded_actions.py` | A tiny example script (two page loads) — the shape of anything the recorder produces. |
| `screenshot.png` | What the recorder window looks like. |

## Step 1 — Record some actions

Activate the shared virtualenv first (once per terminal session):

```bash
source ../.venv/bin/activate
```

```bash
python record.py https://example.com
```

- A Chromium window opens at the given URL (it defaults to
  `https://example.com` if you pass nothing).
- Click around, fill forms, follow links — whatever you want to automate.
- The **Inspector** panel shows the equivalent Python (using
  `sync_playwright`) updating live as you go.
- Close the browser window when you're done; the finished script is written
  to `recorded_actions.py`.

To save somewhere other than `recorded_actions.py`:

```bash
python record.py https://example.com my_script.py
```

## Step 2 — Replay it

```bash
python replay.py
```

This runs `recorded_actions.py` by default, driving a brand-new browser
through exactly the clicks/typing/navigation you recorded. Try it with a
different file too:

```bash
python replay.py my_script.py
```

That is the whole loop: **record once, replay as often as you like** — and
from here a script can grow into a scheduled job (see lesson 02), a test,
or a scraper.

---

> [TODO] Fill in with:
> - a screenshot of the recorder window open on a real site (with the
>   Inspector panel visible),
> - a screenshot of the generated `recorded_actions.py` and, ideally, the
>   Inspector showing the Python for a specific click,
> - a screenshot of the browser replaying,
> - a note that recording needs an *interactive* desktop session — you
>   can't record headless (it's a teaching tool, not part of an
>   unattended run).
