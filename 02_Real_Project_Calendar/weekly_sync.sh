#!/usr/bin/env bash
# Manual one-shot for the lesson repo: fetch the current timetable into
# events.json, then push it into Proton Calendar. This is NOT scheduled - the
# launchd weekly job was removed from this repo - so run it by hand when you
# want a fresh sync. Deps come from the shared repo venv via `uv run`.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== $(date) ==="
uv run python fetch_events.py
uv run python sync_to_proton.py
