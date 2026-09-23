"""
Logs into Blackboard Ultra and scrapes downloadable files from one or more
course pages via Playwright (no REST API - just drives the real UI like a
user would). Reuses the same Vaultwarden -> Microsoft/ADFS login chain as
fetch_due_dates.py; only the post-login behaviour is different.

Workflow per course:
  1. Open /ultra/courses/{id}/outline, expand all collapsed sections so
     every nested content item is listed.
  2. Walk every "/document/" content item in the outline.
  3. For each one, open the document viewer and enumerate its file rows.
     Each row is a kebab ('...') button whose aria-label is
     'More options for '.
  4. Per row, try one of two download paths:
       a. Open the kebab and click 'Download original file' (the standard
          path for documents like PDFs, DOCX, PPTX - routes through a
          signed S3 redirect; we capture the Playwright Download event).
       b. If the menu only has 'Expand image' (image attachments), close
          the menu and GET the inline <img src='.../bbcswebdav/...'> URL
          directly with the authenticated browser context.

Files are saved to <out-dir>/<course-name>/<safe-filename>.

Usage:
    # default: scrape/download the course from the URL Aoife originally shared
    uv run python fetch_blackboard_files.py

    # specific course(s)
    uv run python fetch_blackboard_files.py _59656_1 _12345_1

    # parse a Blackboard URL for the course ID
    uv run python fetch_blackboard_files.py --from-url \\
        'https://worcesterbb.blackboard.com/ultra/courses/_59656_1/outline'

    # first-pass discovery: enumerate files without downloading anything
    uv run python fetch_blackboard_files.py --list-only

Vault master password: pass as --password <pwd>, or omit and read from
Keychain via secrets_helper.py (same as fetch_events.py).
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright

import bw_helper
import secrets_helper
from blackboard_login import start_sso
from config import BITWARDEN_EMAIL, VAULT_ITEM_NAME
from login_flow import perform_login

# The course from the URL Aoife shared - Evidence Informed Teaching.
# Keep this as a default rather than requiring --from-url every time.
DEFAULT_COURSE_ID = "_59656_1"

BASE = "https://worcesterbb.blackboard.com"
OUTLINE = "{base}/ultra/courses/{course_id}/outline"


def safe_filename(name: str) -> str:
    """Turn a content item's display name into a filesystem-safe filename."""
    name = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", name).strip().strip(".")
    return name[:200] or "unnamed"


def course_id_from_url(url: str) -> str:
    """Pull `_59656_1`-style course ID out of any Blackboard course/content URL."""
    m = re.search(r"/ultra/courses/(_[\d_]+_\d+)/", url)
    if not m:
        sys.exit(f"Couldn't find a course ID in URL: {url}")
    return m.group(1)


def get_course_name(page, course_id: str) -> str:
    """The outline page renders the course title in the page header."""
    page.goto(OUTLINE.format(base=BASE, course_id=course_id), wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    # The header lives in a banner-ish region at the top of the SPA shell.
    for sel in ('h1[data-test-id="course-title"]', "h1.bb-page-header", "h1"):
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=4000)
            txt = loc.inner_text().strip()
            if txt:
                return safe_filename(txt)
        except PWTimeout:
            continue
    return course_id  # fallback to ID itself


def expand_all_folders(page) -> None:
    """Click every collapsed folder/section so the outline tree is fully open.

    Blackboard Ultra sections are <button aria-expanded="false"> (or similar);
    clicking them is idempotent, but we re-loop a couple of times in case
    opening one section reveals nested ones that also need opening.

    Uses a native DOM .click() (element.evaluate) rather than Playwright's
    synthetic mouse click: verified live that some folder-toggle buttons
    (Mui-styled "folder-title-{id}" links) simply don't respond to a
    coordinate-based click/keyboard Enter/Space in this app, even when
    Playwright reports them visible and enabled, but do respond to a real
    DOM click() call.
    """
    for _ in range(3):
        clicked_any = False
        for sel in (
            'button[aria-expanded="false"]',
            'button[aria-label*="Expand" i]',
            'button[aria-label*="Open" i]',
        ):
            buttons = page.locator(sel).all()
            for btn in buttons:
                try:
                    if btn.is_visible() and btn.is_enabled():
                        btn.evaluate("el => el.click()")
                        clicked_any = True
                except (PWTimeout, Exception):
                    continue
        if not clicked_any:
            break
        page.wait_for_timeout(400)


def enumerate_documents(page) -> list[dict]:
    """Return [{name, href}, ...] for every document link in the outline."""
    seen: dict[str, str] = {}
    for sel in (
        'a[href*="/document/"]',
        'a[href*="/contents/"]',
        "a[data-content-id]",
    ):
        for link in page.locator(sel).all():
            try:
                href = link.get_attribute("href")
                if not href:
                    continue
                full = href if href.startswith("http") else BASE + href
                if "/document/" not in full and "/contents/" not in full:
                    continue
                name = link.inner_text().strip()
                if not name:
                    # Some entries render title in a nested element.
                    name = link.locator("span, div").first.inner_text().strip()
                seen[full] = name or Path(urlparse(full).path).name
            except Exception:
                continue
    return [{"name": n, "href": h} for h, n in seen.items()]


def list_file_rows(page) -> list[str]:
    """On an open document viewer, every file attachment is represented by a
    kebab ('...') button whose aria-label is 'More options for '.

    Returns the filenames (deduped, ordered as they appear) so we know what
    to expect. No clicks involved - safe to call in --list-only mode.
    """
    seen: dict[str, None] = {}
    kebabs = page.locator('button[aria-label*="More options for" i]').all()
    for b in kebabs:
        try:
            al = b.get_attribute("aria-label") or ""
            # aria-label is "More options for <name>"; strip the prefix.
            name = re.sub(r"^More options for\s+", "", al, flags=re.IGNORECASE).strip()
            if name:
                seen[name] = None
        except Exception:
            continue
    return list(seen.keys())


def list_inline_image_urls(page) -> list[str]:
    """Inline image attachments are rendered as <img src=".../bbcswebdav/...">.
    The URL list, in DOM order, corresponds 1:1 with the kebab filenames in
    the same order (both reflect attachment insertion order). Used as the
    fallback download source when the kebab menu has no 'Download original
    file' item (only 'Expand image')."""
    seen, out = set(), []
    for img in page.locator("img").all():
        src = img.get_attribute("src") or ""
        if "bbcswebdav" in src and src not in seen:
            seen.add(src)
            out.append(src)
    return out


def _unique_dest(target: Path) -> Path:
    """If `target` already exists, append _1, _2, ... before the suffix."""
    if not target.exists():
        return target
    base, ext = target.stem, target.suffix or ""
    n = 1
    while True:
        candidate = target.with_name(f"{base}_{n}{ext}")
        if not candidate.exists():
            return candidate
        n += 1


def download_file_row(page, context, filename: str, target: Path, img_url: str | None) -> bool:
    """Download one attachment row to `target`. Tries two paths:

    1. Click the row's kebab -> 'Download original file' menu item ->
       capture the Playwright Download event (the path Blackboard uses for
       documents like PDFs, DOCX, PPTX). This routes through a signed S3
       redirect; we don't care, we just save whatever comes back.

    2. If the menu only offers 'Expand image' (image attachments), close
       the menu and fetch the inline `bbcswebdav` <img> URL directly using
       the same authenticated browser context - returns the raw bytes.

    Returns True if the file was saved, False otherwise.
    """
    kebab = page.locator(f'button[aria-label="More options for {filename}"]').first
    try:
        kebab.wait_for(state="visible", timeout=5000)
        kebab.click()
    except (PWTimeout, Exception):
        return False
    page.wait_for_timeout(500)

    # Path 1: 'Download original file' menu item (documents).
    dl_item = page.locator('[role="menuitem"]:has-text("Download original file")').first
    if dl_item.count() and dl_item.is_visible():
        try:
            with page.expect_download(timeout=15000) as dl_info:
                dl_item.click(timeout=4000)
            dl = dl_info.value
            dest = _unique_dest(target)
            dl.save_as(str(dest))
            return True
        except (PWTimeout, Exception):
            # Fall through to image path.
            pass

    # Close whatever menu might still be open before trying the fallback.
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)

    # Path 2: image attachment - GET the bbcswebdav URL directly.
    if img_url:
        try:
            resp = context.request.get(img_url)
            if resp.status == 200 and resp.body():
                dest = _unique_dest(target)
                dest.write_bytes(resp.body())
                return True
        except Exception:
            return False
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "course_ids",
        nargs="*",
        default=None,
        help="Course IDs to scrape (e.g. _59656_1). Defaults to the one from "
        "Aoife's original link; ignored if --from-url is set.",
    )
    parser.add_argument(
        "--from-url", help="Parse a Blackboard course/content URL for the course ID"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Enumerate downloadable content but don't actually download",
    )
    parser.add_argument("--item", default=VAULT_ITEM_NAME)
    parser.add_argument("--email", default=BITWARDEN_EMAIL)
    parser.add_argument("-o", "--out-dir", default="blackboard_files")
    parser.add_argument(
        "--password",
        default=None,
        help="Vault master password (else read from Keychain via secrets_helper)",
    )
    args = parser.parse_args()

    if args.from_url:
        course_ids = [course_id_from_url(args.from_url)]
    elif args.course_ids:
        course_ids = args.course_ids
    else:
        course_ids = [DEFAULT_COURSE_ID]

    master_password = args.password or secrets_helper.get_master_password()

    print("Unlocking Vaultwarden...")
    session = bw_helper.get_session(args.email, master_password)
    username = bw_helper.get_field(session, args.item, "username")
    password = bw_helper.get_field(session, args.item, "password")
    totp = bw_helper.get_field(session, args.item, "totp")
    if not username or not password:
        sys.exit(f"Couldn't get a username/password from vault item '{args.item}'.")

    summary: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.list_only)
        context = browser.new_context()
        page = context.new_page()

        print("Logging in to Blackboard...")
        page.goto(
            BASE + "/ultra/courses/" + course_ids[0] + "/outline",
            wait_until="domcontentloaded",
        )
        start_sso(page)
        perform_login(page, username, password, totp)
        # Blackboard's SPA keeps long-polling for notifications, so networkidle
        # never settles. domcontentloaded + a short pause is the real ready signal.
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        for course_id in course_ids:
            print(f"\n=== {course_id} ===")
            course_name = get_course_name(page, course_id)
            print(f"Course name: {course_name}")

            print("Expanding outline sections...")
            expand_all_folders(page)

            docs = enumerate_documents(page)
            print(f"Found {len(docs)} document link(s) in outline.")

            for i, doc in enumerate(docs, 1):
                print(f"\n  [{i}/{len(docs)}] {doc['name']} ({doc['href']})")

                page.goto(doc["href"], wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                file_rows = list_file_rows(page)
                img_urls = list_inline_image_urls(page)
                # Pair each kebab with its implicit img URL by position.
                # The lists should be the same length and in the same order.
                img_for: dict[str, str | None] = {}
                for j, fn in enumerate(file_rows):
                    img_for[fn] = img_urls[j] if j < len(img_urls) else None
                print(f"    {len(file_rows)} file attachment(s)")

                if args.list_only:
                    for fn in file_rows:
                        kind = "image" if img_for[fn] else "doc"
                        print(f"      - [{kind}] {fn}")
                        summary.append(
                            {
                                "course": course_id,
                                "section": doc["name"],
                                "file": fn,
                                "saved_as": None,
                            }
                        )
                    continue

                target_dir = Path(args.out_dir)
                course_dir = target_dir / course_name
                course_dir.mkdir(parents=True, exist_ok=True)

                for j, fn in enumerate(file_rows, 1):
                    print(f"    [{j}/{len(file_rows)}] {fn} ...", end=" ", flush=True)
                    target = course_dir / safe_filename(fn)
                    saved = download_file_row(page, context, fn, target, img_for[fn])
                    if not saved:
                        print("skipped (no download)")
                        summary.append(
                            {
                                "course": course_id,
                                "section": doc["name"],
                                "file": fn,
                                "saved_as": None,
                            }
                        )
                        continue
                    # The actual on-disk filename (after any disambiguation).
                    on_disk = target
                    size_kb = on_disk.stat().st_size / 1024
                    try:
                        shown = on_disk.relative_to(target_dir)
                    except ValueError:
                        shown = on_disk
                    print(f"saved {shown} ({size_kb:.1f} KB)")
                    summary.append(
                        {
                            "course": course_id,
                            "section": doc["name"],
                            "file": fn,
                            "saved_as": str(target),
                        }
                    )

        browser.close()

    print(f"\nDone. Total items seen: {len(summary)}")
    if not args.list_only:
        saved = sum(1 for s in summary if s["saved_as"])
        skipped = len(summary) - saved
        print(f"  Saved:   {saved}")
        print(f"  Skipped: {skipped} (LTI/iframe/HTML - no direct file download)")


if __name__ == "__main__":
    main()
