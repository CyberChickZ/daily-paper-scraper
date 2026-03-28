from __future__ import annotations
import time
import logging
from notion_client import Client

from daily_paper_scraper.models import Paper
from daily_paper_scraper.utils import split_rich_text, retry

logger = logging.getLogger(__name__)


def get_existing_paper_ids(notion: Client, database_id: str) -> set[str]:
    existing = set()
    start_cursor = None
    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = notion.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body=body,
        )
        for page in resp["results"]:
            url = page["properties"].get("arXiv Link", {}).get("url", "")
            if url:
                pid = url.rstrip("/").split("/")[-1]
                existing.add(pid)
        if not resp.get("has_more"):
            break
        start_cursor = resp.get("next_cursor")
    logger.info(f"Notion: {len(existing)} existing papers found")
    return existing


@retry(max_retries=3)
def create_notion_page(paper: Paper, notion: Client, database_id: str) -> str:
    properties = {
        "Name": {"title": [{"text": {"content": paper.title[:2000]}}]},
        "Authors": {"rich_text": split_rich_text(", ".join(paper.authors))},
        "Chinese Summary": {"rich_text": split_rich_text(paper.chinese_summary)},
        "Abstract": {"rich_text": split_rich_text(paper.abstract[:2000])},
        "Categories": {"multi_select": [{"name": c} for c in paper.categories[:10]]},
        "Keywords": {"multi_select": [{"name": k} for k in paper.matched_keywords[:10]]},
        "Source": {"select": {"name": paper.source}},
        "Date": {"date": {"start": paper.published_date} if paper.published_date else None},
        "arXiv Link": {"url": paper.arxiv_url},
        "PDF Link": {"url": paper.pdf_url},
        "Reading Status": {"select": {"name": "Unread"}},
        "Starred": {"checkbox": paper.keyword_score >= 3},
    }
    # Remove None date
    if properties["Date"] is None:
        del properties["Date"]

    page = notion.pages.create(parent={"database_id": database_id}, properties=properties)
    return page["id"]


def sync_papers_to_notion(
    papers: list[Paper],
    notion_token: str,
    database_id: str,
) -> int:
    notion = Client(auth=notion_token)

    existing_ids = get_existing_paper_ids(notion, database_id)
    new_papers = [p for p in papers if p.paper_id not in existing_ids]
    logger.info(f"Notion: {len(new_papers)} new papers to sync (skipped {len(papers) - len(new_papers)} duplicates)")

    synced = 0
    for paper in new_papers:
        try:
            create_notion_page(paper, notion, database_id)
            synced += 1
            logger.info(f"  Synced: {paper.title[:60]}...")
            time.sleep(0.35)
        except Exception as e:
            logger.error(f"  Failed: {paper.paper_id}: {e}")

    logger.info(f"Notion: synced {synced}/{len(new_papers)} papers")
    return synced
