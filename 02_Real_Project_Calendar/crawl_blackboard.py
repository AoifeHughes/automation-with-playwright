"""
Crawls every enrolled Blackboard Ultra course, walking the full outline tree
(recursing into nested topics/modules, not just the flat top-level list
fetch_blackboard_files.py handles) and preserves that tree as nested
directories on disk: <out-dir>/<Course>/<Topic>/.../<Item>/<file>.

Downloads land in ./blackboard_files by default (override with --out-dir).
Moving them into the Obsidian teaching vault afterwards is a manual step,
not something this script does for you.

Safe to rerun: a JSON manifest (blackboard_manifest.json) records which
(course, content item, filename) triples have already been downloaded, so a
rerun only fetches files that are new since the last run.

Usage:
    uv run python crawl_blackboard.py                 # every enrolled course
    uv run python crawl_blackboard.py _59656_1         # just these course(s)
    uv run python crawl_blackboard.py --list-only      # discovery only, no downloads
"""

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import bw_helper
import secrets_helper
from blackboard_login import start_sso
from config import BITWARDEN_EMAIL, VAULT_ITEM_NAME
from fetch_blackboard_files import (
    download_file_row,
    expand_all_folders,
    list_file_rows,
    list_inline_image_urls,
    safe_filename,
)
from login_flow import perform_login

BASE = "https://worcesterbb.blackboard.com"
COURSE_LIST_URL = f"{BASE}/ultra/course"
OUTLINE = "{base}/ultra/courses/{course_id}/outline"
MANIFEST_PATH = Path("blackboard_manifest.json")

# Outline items have no ARIA tree (no role="tree"/"treeitem", no nested
# <ul>/<li>) - everything is a <div data-content-id="_NNNNN_1">, and the only
# way to find an item's parent topic is to walk up the DOM to the nearest
# ancestor that also carries data-content-id. A real topic/folder (of either
# Blackboard content type seen live - "Learning Module" or plain "Folder")
# carries its clean display name in a dedicated "learning-module-title-{id}"
# or "folder-title-{id}" element; a leaf item has neither. Relying on that ID
# lookup instead of a CSS class or aria-labelledby on the row div itself is
# what actually works here - the class/aria-labelledby heuristic looked
# right in isolation but the attributes it expects turned out to live on
# nested elements the row div itself doesn't carry.
TREE_JS = r"""
() => {
  const nodes = Array.from(document.querySelectorAll('[data-content-id]'));
  // querySelector('a[href]') on a folder searches its whole subtree, which
  // - once the folder is expanded and its children are in the DOM - finds a
  // CHILD's anchor instead of correctly reporting "this folder has no href
  // of its own". Only accept an anchor whose path back up to `el` doesn't
  // cross another [data-content-id] boundary (i.e. it isn't a nested row).
  const ownAnchor = (el) => {
    for (const a of el.querySelectorAll('a[href]')) {
      let p = a.parentElement, own = true;
      while (p && p !== el) {
        if (p.hasAttribute && p.hasAttribute('data-content-id')) { own = false; break; }
        p = p.parentElement;
      }
      if (own) return a;
    }
    return null;
  };
  return nodes.map(el => {
    const id = el.getAttribute('data-content-id');
    let p = el.parentElement, parentId = null;
    while (p) {
      if (p.hasAttribute && p.hasAttribute('data-content-id') && p.getAttribute('data-content-id') !== id) {
        parentId = p.getAttribute('data-content-id');
        break;
      }
      p = p.parentElement;
    }
    const anchor = ownAnchor(el);
    const href = anchor ? anchor.getAttribute('href') : null;
    const namedTitleEl = document.getElementById('learning-module-title-' + id)
      || document.getElementById('folder-title-' + id);
    const isTopic = !!namedTitleEl || href === null;
    let title = namedTitleEl ? namedTitleEl.textContent.trim() : null;
    if (title === null) {
      title = anchor ? anchor.textContent.trim() : (el.textContent || '').trim().slice(0, 300);
    }
    return {id, parentId, href, isTopic, title};
  });
}
"""

# Defensive fallback for the rare topic whose title falls through to the
# el.textContent path above (no named-title element found): strip the
# boilerplate Blackboard prepends to a container's accessible name.
_CONTAINER_BOILERPLATE = re.compile(
    r"^This item is a container for other items\.\s*"
    r"It will be marked as completed once all the content items inside have been completed\.\s*"
)

# A leaf's own outline-row wrapper sometimes shares its child's href (both
# point at the same /document/ or /file/ URL) - only the node whose OWN id
# is embedded in the href is the real content item; the wrapper is not a
# topic (it has an href) and not worth visiting again (it's a duplicate of
# its child), so it's simply dropped rather than downloaded twice.
_SELF_HREF_RE = re.compile(r"/(?:document|file)/([\w-]+)")


def is_topic(node: dict) -> bool:
    return bool(node.get("isTopic"))


def topic_title(node: dict) -> str:
    title = node.get("title") or ""
    return _CONTAINER_BOILERPLATE.sub("", title).strip()


def is_self_referential_leaf(content_id: str, node: dict) -> bool:
    href = node.get("href") or ""
    if not re.search(r"/(?:document|file)/", href):
        return False
    m = _SELF_HREF_RE.search(href)
    return bool(m) and m.group(1) == content_id


def discover_courses(page) -> list[dict]:
    """The Ultra "My Courses" list is really the classic Angular course-list
    page; course cards are javascript:void(0) SPA links with no usable href,
    so we read the ID/name off the card and navigate to the outline URL
    directly rather than clicking. A card with no data-course-id is an
    inactive/restricted course - skip it."""
    page.goto(COURSE_LIST_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    courses, seen = [], set()
    for card in page.locator("article[data-course-id]").all():
        cid = card.get_attribute("data-course-id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        name_el = page.locator(f"#course-name-{cid}")
        name = name_el.first.inner_text().strip() if name_el.count() else cid
        courses.append({"id": cid, "name": safe_filename(name)})
    return courses


def build_tree(page) -> dict[str, dict]:
    return {n["id"]: n for n in page.evaluate(TREE_JS) if n["id"]}


def topic_path(tree: dict, content_id: str) -> list[str]:
    """Ancestor topic/folder titles from root down to (not including) content_id
    itself. Ancestors that aren't real topics (e.g. a leaf's own row wrapper,
    which has an href and so fails is_topic) are transparently skipped rather
    than breaking the walk, so a real topic further up is still found."""
    path, seen = [], set()
    cur = tree.get(content_id, {}).get("parentId")
    while cur and cur not in seen:
        seen.add(cur)
        node = tree.get(cur)
        if not node:
            break
        if is_topic(node):
            title = topic_title(node)
            if title:
                path.append(safe_filename(title))
        cur = node.get("parentId")
    path.reverse()
    return path


def render_full_outline(page) -> None:
    """The outline is virtualized (only rows near the viewport are actually in
    the DOM) and folders can be collapsed, so a single expand-all pass doesn't
    reach content that's currently off-screen. Interleave expanding buttons
    with scrolling until both the rendered item count and the outline's
    height stop growing."""
    prev_count, prev_height = -1, -1
    for _ in range(25):
        expand_all_folders(page)
        for _ in range(6):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(300)
        count = page.eval_on_selector_all("[data-content-id]", "els => els.length")
        height = page.evaluate("document.body.scrollHeight")
        if count == prev_count and height == prev_height:
            break
        prev_count, prev_height = count, height


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def manifest_key(course_id: str, content_id: str, filename: str) -> str:
    return f"{course_id}::{content_id}::{filename}"


def crawl_course(
    page, context, course, out_dir: Path, manifest: dict, list_only: bool, stats: dict
):
    course_id, course_name = course["id"], course["name"]
    print(f"\n=== {course_name} ({course_id}) ===")
    page.goto(OUTLINE.format(base=BASE, course_id=course_id), wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    render_full_outline(page)

    tree = build_tree(page)
    # A leaf candidate is any node with a real /document/ or /file/ href; if
    # its outer row wrapper shares that same href, only the self-referential
    # node (the one the href's own id actually names) is kept, so the same
    # file is never visited - and downloaded - twice under two content ids.
    doc_items = [(cid, n) for cid, n in tree.items() if is_self_referential_leaf(cid, n)]
    skip_items = [
        (cid, n)
        for cid, n in tree.items()
        if n.get("href") not in (None,) and not is_topic(n) and not is_self_referential_leaf(cid, n)
    ]
    n_topics = sum(1 for n in tree.values() if is_topic(n))
    print(
        f"Found {len(doc_items)} document item(s) across {n_topics} topic(s) "
        f"({len(skip_items)} other outline row(s) skipped - duplicate row wrappers, "
        f"assignments, or other non-downloadable content)."
    )

    for content_id, node in doc_items:
        topics = topic_path(tree, content_id)
        item_title = safe_filename(node.get("title") or content_id)
        href = node["href"]
        full_href = href if href.startswith("http") else BASE + href
        rel_dir = Path(course_name, *topics, item_title)
        print(f"\n  [{content_id}] {' / '.join(topics + [item_title])}")

        page.goto(full_href, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        file_rows = list_file_rows(page)
        img_urls = list_inline_image_urls(page)
        img_for = {
            fn: (img_urls[i] if i < len(img_urls) else None) for i, fn in enumerate(file_rows)
        }
        print(f"    {len(file_rows)} file attachment(s)")

        for fn in file_rows:
            key = manifest_key(course_id, content_id, fn)
            existing = manifest.get(key)
            if existing and Path(existing["path"]).exists():
                print(f"    - {fn}: already have it, skipping")
                stats["skipped_known"] += 1
                continue

            if list_only:
                print(f"    - {fn}: NEW (not fetched, --list-only)")
                stats["new_listed"] += 1
                continue

            target_dir = out_dir / rel_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / safe_filename(fn)
            print(f"    - {fn}: downloading...", end=" ", flush=True)
            saved = download_file_row(page, context, fn, target, img_for[fn])
            if not saved:
                print("skipped (no direct download)")
                stats["skipped_no_download"] += 1
                continue
            size_kb = target.stat().st_size / 1024
            print(f"saved ({size_kb:.1f} KB)")
            manifest[key] = {
                "path": str(target),
                "size": target.stat().st_size,
                "course": course_name,
                "topics": topics,
                "item": item_title,
            }
            save_manifest(
                manifest
            )  # write after every file so a crash mid-run loses nothing already saved
            stats["downloaded"] += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "course_ids",
        nargs="*",
        default=None,
        help="Specific course IDs; default: every enrolled course",
    )
    parser.add_argument(
        "--list-only", action="store_true", help="Discover and show what's new without downloading"
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

    master_password = args.password or secrets_helper.get_master_password()
    print("Unlocking Vaultwarden...")
    session = bw_helper.get_session(args.email, master_password)
    username = bw_helper.get_field(session, args.item, "username")
    password = bw_helper.get_field(session, args.item, "password")
    totp = bw_helper.get_field(session, args.item, "totp")
    if not username or not password:
        sys.exit(f"Couldn't get a username/password from vault item '{args.item}'.")

    manifest = load_manifest()
    out_dir = Path(args.out_dir)
    stats = {"downloaded": 0, "skipped_known": 0, "skipped_no_download": 0, "new_listed": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Logging in to Blackboard...")
        page.goto(BASE + "/ultra/course", wait_until="domcontentloaded")
        start_sso(page)
        perform_login(page, username, password, totp)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        all_courses = {c["id"]: c for c in discover_courses(page)}
        if args.course_ids:
            courses = [all_courses.get(cid, {"id": cid, "name": cid}) for cid in args.course_ids]
        else:
            courses = list(all_courses.values())
            print(
                f"Discovered {len(courses)} course(s): "
                + ", ".join(f"{c['name']} ({c['id']})" for c in courses)
            )

        for course in courses:
            crawl_course(page, context, course, out_dir, manifest, args.list_only, stats)

        browser.close()

    print("\nDone.")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Already had (skipped): {stats['skipped_known']}")
    print(f"  Skipped (no direct download): {stats['skipped_no_download']}")
    if args.list_only:
        print(f"  New (not fetched, --list-only): {stats['new_listed']}")


if __name__ == "__main__":
    main()
