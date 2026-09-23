"""
Automated version of login.py: pulls the site login (and TOTP, if the vault
item has one configured) from Vaultwarden, then drives the Microsoft/ADFS
login flow for mytimetable.worc.ac.uk. Falls back to a manual pause at the
end so any step it didn't recognise (an extra MFA prompt, a consent screen,
Duo push, etc.) can be finished by hand before the session gets saved.

Usage:
    uv run python login_auto.py <vault-master-password> [--item NAME] [--email EMAIL]

Note: the master password will briefly be visible in `ps` output and in your
shell history while this runs. Fine for local/manual use; don't put this in
a script that another user or process on the same machine could inspect.
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

import bw_helper
from config import BITWARDEN_EMAIL, CALENDAR_URL, STATE_FILE, VAULT_ITEM_NAME
from login_flow import perform_login

parser = argparse.ArgumentParser()
parser.add_argument("master_password", help="Vaultwarden master password")
parser.add_argument("--item", default=VAULT_ITEM_NAME, help="Vault item name or id")
parser.add_argument("--email", default=BITWARDEN_EMAIL)
parser.add_argument(
    "--list", action="store_true", help="List matching items (id/name/username) and exit"
)
args = parser.parse_args()

print("Unlocking Vaultwarden...")
session = bw_helper.get_session(args.email, args.master_password)

if args.list:
    for match in bw_helper.list_matches(session, args.item):
        print(f"  id={match['id']}  name={match['name']!r}  username={match['username']!r}")
    sys.exit(0)

username = bw_helper.get_field(session, args.item, "username")
password = bw_helper.get_field(session, args.item, "password")
totp = bw_helper.get_field(session, args.item, "totp")

if not username or not password:
    sys.exit(
        f"Couldn't get a username/password from vault item '{args.item}' - check the item name."
    )

print(f"Got login for '{username}' (TOTP {'available' if totp else 'not configured'}).")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(CALENDAR_URL)
    perform_login(page, username, password, totp)

    input(
        "\nIf anything still needs finishing (extra MFA step, consent screen, etc.), "
        "complete it now in the browser, then press Enter here...\n"
    )

    context.storage_state(path=STATE_FILE)
    print(f"Saved session to {STATE_FILE}")

    browser.close()
