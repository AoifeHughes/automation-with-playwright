# calendar_scrape

Pulls the PGCE timetable from mytimetable.worc.ac.uk (Microsoft/ADFS login)
and syncs it into Proton Calendar, one calendar per event type.

> NOTE - this is a lesson repo. The unattended `launchd` weekly job that the
> original project had has been **removed here**: the fetch/sync scripts below
> are kept as teaching material and are run by hand with `weekly_sync.sh` (or
> the individual scripts). The login, secret-handling and sync logic is
> unchanged.

## Requirements

- **uv** (Python project/dependency manager) - `brew install uv`
- **Python 3.13** - managed automatically by uv, no separate install needed
- **Playwright + Chromium** - installed into the shared repo `.venv` by `uv sync`
  (run once from the repo root); Chromium itself via `uv run playwright install chromium`
- **Bitwarden CLI (`bw`)** - `brew install bitwarden-cli` - pointed at the
  self-hosted Vaultwarden instance:
  `bw config server https://vaultwarden.tailed5a29.ts.net`, logged in as
  `aoife@terrasen.uk`. The vault holds the mytimetable.worc.ac.uk login
  under the item named "Worc" (id `ebda6e3c-fd05-457a-810e-d5448291173b` -
  there are two items literally named "Worc"; this is the right one, see
  `config.py`).
- **proton-cli** - installed via the upstream install script
  (`curl -fsSL https://raw.githubusercontent.com/roman-16/proton-cli/main/scripts/install.sh | sh`),
  logged in to Proton as `aoife@terrasen.uk`. Docs: https://proton-cli.lerchster.dev/
- **macOS Keychain entry** holding the Vaultwarden master password (see
  Secrets below) - needed to unlock the vault for a run.

Deps come from the repo root `pyproject.toml`/`uv.lock` (run `uv sync` once at
the repo root - see `../..`); there is no per-folder `pyproject.toml` here.

## Files

| File | Purpose |
|---|---|
| `config.py` | Site URL, Vaultwarden item/email, session state file path |
| `bw_helper.py` | Wraps the `bw` CLI: unlock vault, read a field, list matches |
| `secrets_helper.py` | Reads the Vaultwarden master password from Keychain |
| `login_flow.py` | Shared Playwright logic that drives the Microsoft/ADFS login form |
| `login_auto.py` | Manual/interactive login test - opens a visible browser, pauses before saving the session. Debugging tool, not used by the weekly run. |
| `fetch_events.py` | Logs in, loads the timetable, writes `events.json` |
| `sync_to_proton.py` | Pushes `events.json` into Proton Calendar: creates the 3 calendars if missing, imports/updates events, deletes ones no longer in the source |
| `fix_reminders.py` | One-off script (already run) that set the 3 calendars to a 15-min popup reminder only, no email |
| `fetch_due_dates.py`, `sync_due_dates_to_proton.py` | Same pattern as the timetable, for Blackboard assignment due dates -> a separate "Due Dates" calendar |
| `fetch_blackboard_files.py` | Downloads file attachments from one or more Blackboard courses (flat, not recursive) |
| `crawl_blackboard.py` | Auto-discovers every enrolled Blackboard course, recursively walks the full outline (topics/subtopics), and downloads every file attachment into `blackboard_files/<Course>/<Topic>/.../<Item>/<file>`, mirroring Blackboard's own structure. Safe to rerun: `blackboard_manifest.json` tracks what's already been fetched (keyed by course + content item + filename), so a rerun only downloads files that are new since last time. Use `--list-only` to preview what's new without downloading, or pass specific course IDs to limit scope. |
| `weekly_sync.sh` | Manual one-shot: runs `fetch_events.py` then `sync_to_proton.py`, logged to `weekly_sync.log`. (The launchd job that used to run this weekly is not part of this repo.) |
| `login.py`, `fetch.py`, `keychain_test.py`, `explore_events.py` | Earlier prototypes/exploration, kept for reference |

Not committed to git - if you use this project, exclude at minimum (the repo
`.gitignore` already covers these): `.tmp_pass`, `storage_state.json`,
`captured_responses.json`, `events.json`, `*.log`, `.venv/`.

## Secrets

Two secrets are involved, stored two different ways:

1. **The mytimetable.worc.ac.uk login itself** (username/password/TOTP) -
   lives in Vaultwarden, fetched at runtime via `bw`. Nothing to manage here
   day-to-day.
2. **The Vaultwarden master password** - needed to unlock the vault before
   `bw` can read (1). For a run, this is stored in **macOS Keychain** rather
   than a plaintext file, seeded with:

   ```
   security add-generic-password -a "aoife@terrasen.uk" \
       -s "calendar_scrape-vaultwarden" -w '<vault master password>' \
       -T /usr/bin/security -U
   ```

   `-T /usr/bin/security` pre-authorizes the `security` CLI to read it back
   without a GUI "Allow" prompt each time - required for `launchd` to run
   this unattended. This has to be run in a real interactive terminal
   (Keychain write prompts need a real GUI session).

   `fetch_events.py` reads it automatically via `secrets_helper.py` when no
   password is passed on the command line. For a one-off manual run you can
   still override: `uv run python fetch_events.py <password>`.

   `.tmp_pass` (a plaintext file with the same password, used earlier while
   prototyping) is superseded by this and safe to delete once the Keychain
   entry is confirmed working.

## Running it (manually)

Neither step is scheduled in this lesson repo - run them by hand whenever
you want a fresh sync:

    uv run python fetch_events.py
    uv run python sync_to_proton.py

`fetch_events.py` logs in (Keychain password → Vaultwarden → site login →
Playwright drives the Microsoft/ADFS form) and writes the current timetable
to `events.json`.

`sync_to_proton.py` then, for each event type (Lecture/Seminar/Online):
- creates the Proton calendar if it doesn't exist yet, colour-coded,
  with a popup-only 15-min reminder;
- imports events, matched by UID, so **changed times/locations/titles
  update the existing event** rather than duplicating it;
- then deletes any previously-synced event whose UID is no longer in the
  fresh `events.json` (e.g. a cancelled session).

So update/delete/edit is handled each run. `weekly_sync.sh` just runs both
scripts in order and appends to `weekly_sync.log` (see it for the exact
commands).

### Next academic year

`TIMETABLE_URL` in `fetch_events.py` and the stale-event date range in
`sync_to_proton.py` are both hardcoded to the 2026-27 academic year
(`datePeriod=all year (26-27)`, `2026-08-01`..`2027-08-31`). Update both
when the new year's timetable is published.
