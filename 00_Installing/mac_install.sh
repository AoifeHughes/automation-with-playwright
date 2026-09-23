#!/usr/bin/env bash
# Install Playwright + Chromium into the shared repo environment (uv).
#
# There is one virtualenv for the whole repo, at the repo root (.venv/),
# created by `uv sync` from pyproject.toml. Every lesson reuses it rather
# than building its own.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Creating the shared environment with 'uv sync' (installs playwright + icalendar)"
uv sync

echo "==> Installing the Chromium browser binary (this may take a while)"
uv run playwright install chromium

echo ""
echo "==> Done. Run any lesson script with, e.g.:"
echo "    uv run python 01_First_Use/record.py [url]"
echo "    uv run python 02_Real_Project_Calendar/fetch_events.py"
echo "    # or activate the shared venv once:"
echo "    source ../.venv/bin/activate      # from a lesson folder"
echo "    source .venv/bin/activate         # from the repo root"
