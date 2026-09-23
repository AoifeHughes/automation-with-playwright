#!/usr/bin/env bash
# Runs the lesson-03 example against the shared repo venv. The script prompts
# you for the mytimetable login on the command line, so there's nothing to
# pre-configure - no password file, no `bw` CLI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -d "$REPO_ROOT/.venv" ]; then
    echo "==> No shared .venv found - run 00_Installing/mac_install.sh first." >&2
    exit 1
fi

cd "$SCRIPT_DIR"
"$REPO_ROOT/.venv/bin/python" calendar_example.py
