#!/usr/bin/env python3
"""One-time script to create the Notion database with the correct schema."""
import os
import sys
from notion_client import Client


def main():
    token = os.environ.get("NOTION_TOKEN")
    parent_page_id = os.environ.get("NOTION_PARENT_PAGE_ID")

    if not token or not parent_page_id:
        print("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID environment variables")
        sys.exit(1)

    notion = Client(auth=token)

    properties = {
        "Title": {"title": {}},
        "Authors": {"rich_text": {}},
        "Chinese Summary": {"rich_text": {}},
        "Abstract": {"rich_text": {}},
        "Categories": {"multi_select": {"options": [
            {"name": "cs.CV"}, {"name": "cs.GR"}, {"name": "cs.RO"},
            {"name": "cs.AI"}, {"name": "cs.LG"},
        ]}},
        "Keywords": {"multi_select": {"options": []}},
        "Source": {"select": {"options": [
            {"name": "arXiv"}, {"name": "HuggingFace"},
        ]}},
        "Date": {"date": {}},
        "arXiv Link": {"url": {}},
        "PDF Link": {"url": {}},
        "Reading Status": {"select": {"options": [
            {"name": "Unread"}, {"name": "Reading"}, {"name": "Done"},
        ]}},
        "Starred": {"checkbox": {}},
    }

    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Daily Papers Database"}}],
        properties=properties,
    )

    print(f"Database created successfully!")
    print(f"Database ID: {db['id']}")
    print(f"Set this as NOTION_DATABASE_ID in your environment.")


if __name__ == "__main__":
    main()
