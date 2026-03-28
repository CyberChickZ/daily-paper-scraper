#!/usr/bin/env python3
"""Bulk sync papers to Notion using requests (more reliable than notion-client with Python 3.14 SSL)."""
import json
import os
import sys
import time
import requests

NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def split_text(text, limit=2000):
    chunks = []
    for i in range(0, len(text), limit):
        chunks.append({"type": "text", "text": {"content": text[i:i+limit]}})
    return chunks or [{"type": "text", "text": {"content": ""}}]


def get_existing_ids(token, db_id):
    """Get all existing paper IDs from Notion database."""
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    existing = set()
    start_cursor = None
    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = requests.post(f"{NOTION_API}/databases/{db_id}/query", headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        for page in data["results"]:
            url = page["properties"].get("arXiv Link", {}).get("url", "")
            if url:
                pid = url.rstrip("/").split("/")[-1]
                existing.add(pid)
        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
    return existing


def create_page(token, db_id, paper):
    """Create a Notion page for a paper."""
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    properties = {
        "Name": {"title": [{"text": {"content": paper["title"][:2000]}}]},
        "Authors": {"rich_text": split_text(", ".join(paper.get("authors", []))[:2000])},
        "Chinese Summary": {"rich_text": split_text(paper.get("chinese_summary", ""))},
        "Abstract": {"rich_text": split_text(paper.get("abstract", "")[:2000])},
        "Categories": {"multi_select": [{"name": c} for c in paper.get("categories", [])[:10]]},
        "Keywords": {"multi_select": [{"name": k} for k in paper.get("matched_keywords", [])[:10]]},
        "Source": {"select": {"name": paper.get("source", "arXiv")}},
        "arXiv Link": {"url": paper.get("arxiv_url", "")},
        "PDF Link": {"url": paper.get("pdf_url", "")},
        "Reading Status": {"select": {"name": "Unread"}},
        "Starred": {"checkbox": paper.get("keyword_score", 0) >= 3},
    }
    if paper.get("published_date"):
        properties["Date"] = {"date": {"start": paper["published_date"]}}

    body = {"parent": {"database_id": db_id}, "properties": properties}
    resp = requests.post(f"{NOTION_API}/pages", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["id"]


def main():
    import yaml
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    token = os.environ.get("NOTION_TOKEN") or cfg["notion"]["token"]
    db_id = os.environ.get("NOTION_DATABASE_ID") or cfg["notion"]["database_id"]
    input_file = sys.argv[1] if len(sys.argv) > 1 else "papers_with_summary.json"

    with open(input_file, "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"Loaded {len(papers)} papers from {input_file}")

    # Dedup against existing
    existing = get_existing_ids(token, db_id)
    print(f"Found {len(existing)} existing papers in Notion")
    new_papers = [p for p in papers if p["paper_id"] not in existing]
    print(f"Will sync {len(new_papers)} new papers")

    synced = 0
    errors = 0
    for i, paper in enumerate(new_papers):
        try:
            create_page(token, db_id, paper)
            synced += 1
            if synced % 50 == 0:
                print(f"  Progress: {synced}/{len(new_papers)} synced...")
            time.sleep(0.35)
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error on {paper['paper_id']}: {e}")
            time.sleep(1)

    print(f"Done: {synced} synced, {errors} errors, out of {len(new_papers)} new papers")


if __name__ == "__main__":
    main()
