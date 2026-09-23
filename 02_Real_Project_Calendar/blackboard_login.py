"""Blackboard-specific steps before handing off to the shared Microsoft/ADFS
login flow in login_flow.py. Blackboard doesn't redirect to Microsoft
immediately - it shows its own login form first, with SSO tucked under a
'Sign in with a third-party account' accordion."""


def start_sso(page):
    page.locator('button:has-text("OK")').first.click(timeout=5000)  # cookie consent
    page.wait_for_timeout(500)
    page.locator("text=Sign in with a third-party account").first.click(timeout=5000)
    page.wait_for_timeout(500)
    page.locator("text=University SSO Login").first.click(timeout=5000)
    page.wait_for_load_state("networkidle", timeout=30000)
