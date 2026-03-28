#!/usr/bin/env python3
"""Read papers JSON (with chinese_summary filled) and sync to Notion."""
import argparse
import sys

from daily_paper_scraper.config import load_config
from daily_paper_scraper.models import papers_from_json
from daily_paper_scraper.notion_sync import sync_papers_to_notion
from daily_paper_scraper.utils import setup_logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="papers_with_summary.json")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    setup_logging()
    cfg = load_config(args.config)

    token = cfg["notion"]["token"]
    db_id = cfg["notion"]["database_id"]
    if not token or not db_id:
        print("Error: notion.token and notion.database_id must be set in config.yaml or env")
        sys.exit(1)

    papers = papers_from_json(args.input)
    print(f"Read {len(papers)} papers from {args.input}")

    synced = sync_papers_to_notion(papers, token, db_id)
    print(f"Done: synced {synced} papers to Notion")


if __name__ == "__main__":
    main()
