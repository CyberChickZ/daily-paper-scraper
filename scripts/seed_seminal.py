#!/usr/bin/env python3
"""Seed seminal papers into Notion database from YAML."""
import yaml
from notion_api import NotionAPI


def main():
    api = NotionAPI()

    with open("data/seminal_papers.yaml") as f:
        data = yaml.safe_load(f)

    # Build existing title→page_id map for Builds On linking
    print("Querying existing papers...")
    pages = api.query_database()
    title_to_id = {}
    for page in pages:
        title_parts = page["properties"].get("Name", {}).get("title", [])
        if title_parts:
            title_to_id[title_parts[0]["plain_text"].strip().lower()] = page["id"]
    print(f"Found {len(title_to_id)} existing papers")

    all_papers = []
    for line_key in ["body_models", "hpe_mesh", "motion_physics"]:
        all_papers.extend(data.get(line_key, []))

    created = 0
    skipped = 0
    for p in all_papers:
        # Check if already exists (by title match)
        if p["title"].strip().lower() in title_to_id:
            # Update Research Line and Evolution Note on existing
            page_id = title_to_id[p["title"].strip().lower()]
            props = {
                "Research Line": {"select": {"name": p["research_line"]}},
                "Evolution Note": {"rich_text": api.rich_text(p.get("evolution_note", ""))},
            }
            if p.get("chinese_summary"):
                props["Chinese Summary"] = {"rich_text": api.rich_text(p["chinese_summary"])}
            api.update_page(page_id, props)
            print(f"  Updated: {p['title'][:60]}")
            skipped += 1
            continue

        # Create new page
        props = {
            "Name": {"title": [{"text": {"content": p["title"]}}]},
            "Authors": {"rich_text": api.rich_text(p.get("authors", ""))},
            "Chinese Summary": {"rich_text": api.rich_text(p.get("chinese_summary", ""))},
            "Source": {"select": {"name": "arXiv"}},
            "arXiv Link": {"url": p.get("arxiv_url", "")},
            "Research Line": {"select": {"name": p["research_line"]}},
            "Evolution Note": {"rich_text": api.rich_text(p.get("evolution_note", ""))},
            "Reading Status": {"select": {"name": "Unread"}},
            "Starred": {"checkbox": True},
            "Followed": {"checkbox": False},
            "Favorite": {"checkbox": True},  # Seminal papers auto-favorited
        }
        if p.get("pdf_url"):
            props["PDF Link"] = {"url": p["pdf_url"]}

        result = api.create_page(props)
        new_id = result["id"]
        title_to_id[p["title"].strip().lower()] = new_id
        print(f"  Created: {p['title'][:60]}")
        created += 1

    # Second pass: set Builds On relations
    print("\nSetting Builds On relations...")
    linked = 0
    for p in all_papers:
        if not p.get("builds_on"):
            continue
        page_id = title_to_id.get(p["title"].strip().lower())
        parent_id = None
        # Search for parent by partial title match
        builds_on = p["builds_on"].lower()
        for t, pid in title_to_id.items():
            if builds_on in t:
                parent_id = pid
                break
        if page_id and parent_id:
            api.update_page(page_id, {"Builds On": {"relation": [{"id": parent_id}]}})
            print(f"  Linked: {p['title'][:40]} → {p['builds_on']}")
            linked += 1

    print(f"\nDone: {created} created, {skipped} updated, {linked} relations linked")


if __name__ == "__main__":
    main()
