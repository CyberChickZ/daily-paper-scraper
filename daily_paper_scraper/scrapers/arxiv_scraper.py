from __future__ import annotations
import arxiv
from datetime import date, timedelta
import logging

from daily_paper_scraper.models import Paper

logger = logging.getLogger(__name__)


def _result_to_paper(result) -> Paper:
    pid = result.get_short_id().split("v")[0]
    return Paper(
        paper_id=pid,
        title=result.title,
        authors=[a.name for a in result.authors[:10]],
        abstract=result.summary,
        categories=[c for c in result.categories],
        published_date=result.published.date().isoformat(),
        arxiv_url=result.entry_id,
        pdf_url=result.pdf_url or f"https://arxiv.org/pdf/{pid}",
        source="arXiv",
    )


def fetch_arxiv_papers(
    categories: list[str],
    target_date: date,
    max_results: int = 200,
) -> list[Paper]:
    """Daily mode: fetch by category + date."""
    client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=3)
    all_papers: dict[str, Paper] = {}

    date_from = target_date.strftime("%Y%m%d") + "0000"
    date_to = (target_date + timedelta(days=1)).strftime("%Y%m%d") + "2359"

    for cat in categories:
        query = f"cat:{cat} AND submittedDate:[{date_from} TO {date_to}]"
        logger.info(f"Querying arXiv: {query}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )

        try:
            for result in client.results(search):
                p = _result_to_paper(result)
                if p.paper_id not in all_papers:
                    all_papers[p.paper_id] = p
        except Exception as e:
            logger.warning(f"Error fetching {cat}: {e}")

    logger.info(f"arXiv: fetched {len(all_papers)} unique papers")
    return list(all_papers.values())


def fetch_arxiv_by_keywords(
    keywords: list[str],
    date_from: date,
    date_to: date,
    max_results_per_keyword: int = 500,
) -> list[Paper]:
    """Backfill mode: search by keywords across a date range. Much more efficient for historical data."""
    client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=3)
    all_papers: dict[str, Paper] = {}

    dfrom = date_from.strftime("%Y%m%d") + "0000"
    dto = date_to.strftime("%Y%m%d") + "2359"
    date_filter = f"submittedDate:[{dfrom} TO {dto}]"

    for kw in keywords:
        # Search in title and abstract
        if " " in kw:
            kw_query = f'all:"{kw}"'
        else:
            kw_query = f"all:{kw}"

        query = f"{kw_query} AND {date_filter}"
        logger.info(f"Backfill query: {query}")

        search = arxiv.Search(
            query=query,
            max_results=max_results_per_keyword,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )

        try:
            count = 0
            for result in client.results(search):
                p = _result_to_paper(result)
                if p.paper_id not in all_papers:
                    all_papers[p.paper_id] = p
                    count += 1
            logger.info(f"  '{kw}': {count} new papers")
        except Exception as e:
            logger.warning(f"Error fetching keyword '{kw}': {e}")

    logger.info(f"Backfill: fetched {len(all_papers)} unique papers total")
    return list(all_papers.values())
