"""
Thin wrapper around the `bw` CLI for pulling a login + TOTP code out of
Vaultwarden. Never prints secret values - callers get them back as strings
to use directly, not to display.
"""

import json
import subprocess


def _run(*args, input_text=None):
    result = subprocess.run(
        ["bw", *args],
        input=input_text,
        capture_output=True,
        text=True,
    )
    return result


def get_session(email: str, master_password: str) -> str:
    """Log in (if needed) and unlock the vault, returning a session key."""
    status = json.loads(_run("status").stdout).get("status")

    if status == "unauthenticated":
        result = _run("login", email, master_password, "--raw")
    elif status == "locked":
        result = _run("unlock", master_password, "--raw")
    else:
        raise RuntimeError(
            f"Unexpected vault status '{status}' - if it's already 'unlocked' "
            "from another process, export its BW_SESSION instead of calling this."
        )

    if result.returncode != 0:
        raise RuntimeError(f"bw login/unlock failed: {result.stderr.strip()}")

    return result.stdout.strip()


def list_matches(session: str, search: str) -> list[dict]:
    """Returns [{id, name, username}] for items matching `search` - no secrets."""
    result = _run("list", "items", "--search", search, "--session", session)
    if result.returncode != 0:
        raise RuntimeError(f"bw list items failed: {result.stderr.strip()}")
    items = json.loads(result.stdout)
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "username": (item.get("login") or {}).get("username"),
        }
        for item in items
    ]


def get_field(session: str, item: str, field: str) -> str | None:
    """field is one of: username, password, totp."""
    result = _run("get", field, item, "--session", session)
    if result.returncode != 0:
        print(f"  bw get {field} '{item}' failed: {result.stderr.strip()}")
        return None
    return result.stdout.strip()
