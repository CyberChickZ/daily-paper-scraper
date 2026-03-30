#!/usr/bin/env python3
"""Fetch papers from arXiv and HuggingFace, filter by keywords, output JSON."""
import argparse
import os
from datetime import date, timedelta

from daily_paper_scraper.config import load_config
from daily_paper_scraper.models import papers_to_json
from daily_paper_scraper.scrapers.arxiv_scraper import fetch_arxiv_papers, fetch_arxiv_by_keywords
from daily_paper_scraper.scrapers.hf_scraper import fetch_hf_daily_papers
from daily_paper_scraper.filter import merge_sources, filter_papers
from daily_paper_scraper.focus_tracker import get_focus_papers, extract_dynamic_keywords
from daily_paper_scraper.utils import setup_logging


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="papers.json")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--backfill", action="store_true", help="Backfill mode: search by keywords across date range")
    parser.add_argument("--from-date", type=str, default="2020-01-01", help="Start date for backfill (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, default=None, help="End date for backfill (YYYY-MM-DD), defaults to today")
    parser.add_argument("--max-per-keyword", type=int, default=500, help="Max results per keyword in backfill mode")
    args = parser.parse_args()

    setup_logging()
    cfg = load_config(args.config)

    if args.backfill:
        # Backfill mode: keyword search across date range
        from_date = date.fromisoformat(args.from_date)
        to_date = date.fromisoformat(args.to_date) if args.to_date else date.today()
        print(f"Backfill mode: {from_date} to {to_date}")

        arxiv_papers = fetch_arxiv_by_keywords(
            keywords=cfg["arxiv"]["keywords"],
            date_from=from_date,
            date_to=to_date,
            max_results_per_keyword=args.max_per_keyword,
        )
        # In backfill mode, papers already match keywords, but we still score them
        filtered = filter_papers(
            papers=arxiv_papers,
            keywords=cfg["arxiv"]["keywords"],
            min_score=1,
            hf_always_include=False,
        )
    else:
        # Daily mode: keyword search within 25h window
        target_date = date.today()

        # Merge static keywords + dynamic keywords from Focus papers
        all_keywords = list(cfg["arxiv"]["keywords"])
        token = os.environ.get("NOTION_TOKEN", "")
        db_id = os.environ.get("NOTION_DATABASE_ID", "")
        if token and db_id:
            focus_papers = get_focus_papers(token, db_id)
            dynamic_kw = extract_dynamic_keywords(focus_papers)
            all_keywords.extend(dynamic_kw)
            print(f"Keywords: {len(cfg['arxiv']['keywords'])} static + {len(dynamic_kw)} from {len(focus_papers)} focus papers")

        arxiv_papers = fetch_arxiv_papers(
            categories=cfg["arxiv"]["categories"],
            target_date=target_date,
            max_results=cfg["arxiv"]["max_results_per_category"],
            keywords=all_keywords,
        )

        hf_papers = []
        if cfg["huggingface"]["enabled"]:
            hf_papers = fetch_hf_daily_papers(cfg["huggingface"]["api_url"])

        merged = merge_sources(arxiv_papers, hf_papers)

        filtered = filter_papers(
            papers=merged,
            keywords=all_keywords,
            min_score=cfg["pipeline"]["min_keyword_score"],
            hf_always_include=cfg["pipeline"]["hf_always_include"],
        )

    papers_to_json(filtered, args.output)
    print(f"Wrote {len(filtered)} papers to {args.output}")


if __name__ == "__main__":
    main()
