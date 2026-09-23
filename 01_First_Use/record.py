#!/usr/bin/env python3
"""Record browser actions into a Playwright Python script.

Usage:
    python record.py [url] [output_file]

Opens a browser window; every click, type, and navigation you make is
turned into Python code and saved to output_file (default:
recorded_actions.py). Close the browser window when you're done.
"""

import subprocess
import sys

url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
output_file = sys.argv[2] if len(sys.argv) > 2 else "recorded_actions.py"

print(f"==> Launching codegen recorder against {url}")
print("    Interact with the browser window; close it when done.")
print(f"    Recorded Python code will be saved to {output_file}")

subprocess.run(
    ["playwright", "codegen", "--target", "python", "-o", output_file, url],
    check=True,
)

print(f"==> Done. Replay it with: python replay.py {output_file}")
