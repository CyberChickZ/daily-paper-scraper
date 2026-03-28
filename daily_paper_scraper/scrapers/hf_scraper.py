from __future__ import annotations
import requests
from datetime import datetime
import logging

from daily_paper_scraper.models import Paper

logger = logging.getLogger(__name__)


def fetch_hf_daily_papers(api_url: str = "https://huggingface.co/api/daily_papers") -> list[Paper]:
    logger.info("Fetching HuggingFace daily papers...")
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        entries = resp.json()
    except Exception as e:
        logger.warning(f"HuggingFace fetch failed: {e}")
        return []

    papers = []
    for entry in entries:
        p = entry.get("paper", {})
        pid = p.get("id", "")
        if not pid:
            continue

        published = p.get("publishedAt", "")
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00")).date().isoformat()
        except (ValueError, AttributeError):
            pub_date = ""

        papers.append(Paper(
            paper_id=pid,
            title=p.get("title", ""),
            authors=[a.get("name", "") for a in p.get("authors", [])[:10]],
            abstract=p.get("summary", ""),
            categories=[],
            published_date=pub_date,
            arxiv_url=f"https://arxiv.org/abs/{pid}",
            pdf_url=f"https://arxiv.org/pdf/{pid}",
            source="HuggingFace",
            hf_upvotes=p.get("upvotes", 0),
        ))

    logger.info(f"HuggingFace: fetched {len(papers)} papers")
    return papers
