"""Shared Microsoft/ADFS login-form automation for mytimetable.worc.ac.uk."""

from playwright.sync_api import TimeoutError as PWTimeout


def try_fill(page, selectors, value, timeout=4000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.fill(value)
            return True
        except PWTimeout:
            continue
    return False


def try_click(page, selectors, timeout=4000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            return True
        except PWTimeout:
            continue
    return False


def perform_login(page, username, password, totp=None):
    """Drives mytimetable.worc.ac.uk's 'Log in' button through the
    Microsoft/ADFS form. Assumes page is already at CALENDAR_URL."""
    try_click(
        page,
        [
            "button:has-text('Log in')",
            "a:has-text('Log in')",
            "a:has-text('Login')",
            "button:has-text('Sign in')",
        ],
        timeout=6000,
    )

    try_fill(
        page,
        ["input[name='loginfmt']", "#userNameInput", "input[type='email']"],
        username,
        timeout=8000,
    )
    try_click(page, ["#idSIButton9", "#submitButton", "button:has-text('Next')"], timeout=4000)

    try_fill(
        page,
        ["input[name='passwd']", "#passwordInput", "input[type='password']"],
        password,
        timeout=8000,
    )
    try_click(page, ["#idSIButton9", "#submitButton", "button:has-text('Sign in')"], timeout=4000)

    if totp:
        filled = try_fill(
            page,
            ["input[name='otc']", "#idTxtBx_SAOTCC_OTC", "input[autocomplete='one-time-code']"],
            totp,
            timeout=6000,
        )
        if filled:
            try_click(
                page,
                ["#idSubmit_SAOTCC_Continue", "#idSIButton9", "button:has-text('Verify')"],
                timeout=4000,
            )

    try_click(page, ["#idSIButton9", "button:has-text('Yes')"], timeout=5000)
