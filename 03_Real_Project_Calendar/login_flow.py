"""Prompt-driven wait for the user to finish the Microsoft/ADFS login flow.

Used by fetch_events.py and fetch_due_dates.py. The flow is: the script
opens a headed browser, it lands on the Microsoft login form, the user
types their credentials (and 2FA), and this helper blocks until the URL
comes back to the app we redirected from. No credentials, env vars, vault,
or system password store are involved.
"""

from playwright.sync_api import Page

PROMPT = (
    "Please sign in to your university account in the browser window that just opened.\n"
    "Use your usual username and password (and 2FA if prompted).\n"
    "The script will continue automatically once you're signed in."
)

_LOGIN_HOST = "login.microsoftonline.com"
_LOGIN_HOST_ALT = "login.live.com"
_PROMPT_DEADLINE_MS = 30_000
_POLL_MS = 1_000


def _on_login_host(page: Page) -> bool:
    url = page.url.lower()
    return _LOGIN_HOST in url or _LOGIN_HOST_ALT in url


def wait_for_user_login(page: Page, fallback_pause: bool = True) -> None:
    """Block until the user has finished the Microsoft/ADFS login flow.

    Assumes the browser has already been navigated (or redirected) to a
    Microsoft login URL. Polls page.url; once it leaves login.microsoftonline
    .com / login.live.com, the user is signed in. If fallback_pause is True
    and the URL is still on a login host after ~30s (some intermediate SSO
    bounce our host check doesn't recognise), drop to input() so the user
    can press Enter once they're done.
    """
    print(PROMPT)

    elapsed = 0
    while _on_login_host(page):
        if elapsed >= _PROMPT_DEADLINE_MS:
            break
        page.wait_for_timeout(_POLL_MS)
        elapsed += _POLL_MS

    if _on_login_host(page) and fallback_pause:
        input(
            "\nIf anything still needs finishing (extra MFA, consent screen, etc.), "
            "complete it in the browser, then press Enter here to continue...\n"
        )
