"""
Fetches the Vaultwarden master password from macOS Keychain, so the weekly
automated run needs no password typed or passed in.

Seed it once (run yourself in a real terminal - Keychain write prompts need
a real GUI session, this can't be done from an automated tool call):

    security add-generic-password -a "aoife@terrasen.uk" \\
        -s "calendar_scrape-vaultwarden" -w '<vault master password>' \\
        -T /usr/bin/security -U

-T /usr/bin/security pre-authorizes the `security` CLI itself to read the
item without a GUI prompt each time, which is what makes unattended (cron/
launchd) runs possible.
"""

import subprocess

KEYCHAIN_SERVICE = "calendar_scrape-vaultwarden"
KEYCHAIN_ACCOUNT = "aoife@terrasen.uk"


def get_master_password() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", KEYCHAIN_ACCOUNT, "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Couldn't read '{KEYCHAIN_SERVICE}' from Keychain ({result.stderr.strip()}). "
            "Seed it first - see the docstring at the top of secrets_helper.py."
        )
    return result.stdout.strip()
