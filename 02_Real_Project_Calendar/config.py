CALENDAR_URL = "https://mytimetable.worc.ac.uk/"

# Where the logged-in session (cookies/localStorage) gets saved after login.py,
# and reused by fetch.py. Don't commit or share this file anywhere - it's
# equivalent to a login token for the Microsoft account.
STATE_FILE = "storage_state.json"

# Vaultwarden (self-hosted Bitwarden) account used to fetch the site login.
BITWARDEN_EMAIL = "aoife@terrasen.uk"

# Vault item holding the mytimetable.worc.ac.uk login (username/password,
# and a TOTP field if 2FA is configured on it). Using the id, not the name
# "Worc", since two items share that name.
VAULT_ITEM_NAME = "ebda6e3c-fd05-457a-810e-d5448291173b"
