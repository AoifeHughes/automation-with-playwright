"""
Quick test of pulling a password out of macOS Keychain (including
iCloud Keychain-synced items) via the `security` CLI - no Playwright
involved, just checking access works before relying on it anywhere.

Usage:
    uv run python keychain_test.py <server-or-service-name>

The first time you run this for a given item, macOS will pop up a dialog
asking whether "security"/your terminal app may access that Keychain item -
you need to approve it (Always Allow makes future runs silent).

Only prints whether it was found and how long it is - never the value
itself, so it's safe to run with someone watching your terminal.
"""

import subprocess
import sys

if len(sys.argv) != 2:
    print("Usage: uv run python keychain_test.py <server-or-service-name>")
    sys.exit(1)

target = sys.argv[1]

# Try as an internet password first (what's used for website logins),
# falling back to a generic password (what's used for app/service logins).
for label, args in [
    ("internet password", ["find-internet-password", "-s", target, "-w"]),
    ("generic password", ["find-generic-password", "-s", target, "-w"]),
]:
    result = subprocess.run(["security", *args], capture_output=True, text=True)
    if result.returncode == 0:
        value = result.stdout.strip()
        print(f"Found a {label} for '{target}' ({len(value)} characters).")
        break
else:
    print(f"No Keychain item found for '{target}' as either an internet or generic password.")
    print("Tip: this needs to match the domain/service the item is actually saved under -")
    print("check in Keychain Access.app if unsure.")
