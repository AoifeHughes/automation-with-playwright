# Lesson 00 — Installing Playwright

## Objective

By the end of this lesson you will have Playwright and a working Chromium
browser installed, inside a virtual environment, ready to record and replay
browser scripts (lesson 01).

## What a virtualenv is (briefly)

A virtualenv (`.venv/`) is an isolated Python environment so this project's
dependencies don't clash with anything else on your machine. Each lesson
folder that runs scripts has its own, created by the installer below.

## Files in this lesson

| File | Purpose |
|------|---------|
| `mac_install.sh` | Creates `.venv`, installs the `playwright` package, and downloads the Chromium binary (macOS / Linux). |
| `windows_install.bat` | Same, on Windows. |

Playwright ships its own browser binaries rather than reusing a browser
already on your machine, so "install Playwright" also means "download the
Chromium binary" — a separate download step.

## Steps

```bash
# macOS / Linux
./mac_install.sh
```

```bat
# Windows
windows_install.bat
```

Then activate the shared virtualenv (it lives at the repo root) before running
any script:

```bash
source ../.venv/bin/activate     # from any lesson folder
```

## Verify it worked

```bash
python -c "from playwright.sync_api import sync_playwright; print('ok')"
```

If that prints `ok` you're ready for lesson 01.
