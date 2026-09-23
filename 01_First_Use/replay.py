#!/usr/bin/env python3
"""Replay a recorded Playwright script.

Usage:
    python replay.py [script_file]

Runs the given script (default: recorded_actions.py), driving a fresh
browser through the same sequence of actions it recorded.
"""

import subprocess
import sys

script_file = sys.argv[1] if len(sys.argv) > 1 else "recorded_actions.py"

print(f"==> Replaying {script_file}")
subprocess.run([sys.executable, script_file], check=True)
