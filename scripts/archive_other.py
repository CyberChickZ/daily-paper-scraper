#!/usr/bin/env python3
"""Mark all papers with Research Line == 'Other' as Read in Notion.

These slipped through an over-broad keyword filter and are not relevant to the
3D human / motion research lines. Marking them Read hides them from the default
unread view but keeps them queryable.

Usage:
    set -a && source .env && set +a
    python scripts/archive_other.py --dry-run    # preview
    python scripts/archive_other.py              # apply
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error


NOTION_API = "https://api.notion.com/v1"


def notion_req(method: str, path: str, body=None, token: str = ""):
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")[:300]
            print(f"  Notion HTTP {e.code}: {text}", file=sys.stderr)
            if e.code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception as e:
            print(f"  Notion error: {e}", file=sys.stderr)
            time.sleep(1)
    raise RuntimeError(f"Notion request failed: {method} {path}")


def query_all(token: str, db_id: str) -> list[dict]:
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion_req("POST", f"databases/{db_id}/query", body, token)
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-empty", action="store_true",
                        help="Also archive papers with no research_line set")
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN", "")
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    if not (token and db_id):
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID required", file=sys.stderr)
        sys.exit(1)

    print("Querying Notion...")
    pages = query_all(token, db_id)
    print(f"  {len(pages)} total")

    targets = []
    for page in pages:
        props = page["properties"]
        rl = (props.get("Research Line", {}).get("select") or {}).get("name", "")
        is_read = props.get("Read", {}).get("checkbox", False)
        if is_read:
            continue
        if rl == "Other" or (args.include_empty and not rl):
            title_parts = props.get("Name", {}).get("title", [])
            title = title_parts[0]["plain_text"] if title_parts else ""
            targets.append((page["id"], title, rl or "(empty)"))

    print(f"  {len(targets)} unread papers to archive")
    if not targets:
        return

    for n, (pid, title, rl) in enumerate(targets, 1):
        print(f"[{n}/{len(targets)}] [{rl}] {title[:80]}")
        if args.dry_run:
            continue
        try:
            notion_req(
                "PATCH",
                f"pages/{pid}",
                {"properties": {"Read": {"checkbox": True}}},
                token,
            )
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            continue
        time.sleep(0.35)

    print(f"\nDone: {'(dry-run, no writes)' if args.dry_run else 'archived ' + str(len(targets))}")


if __name__ == "__main__":
    main()
