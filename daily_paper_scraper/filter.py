from __future__ import annotations
import logging

from daily_paper_scraper.models import Paper

logger = logging.getLogger(__name__)


def score_paper(paper: Paper, keywords: list[str]) -> Paper:
    text = (paper.title + " " + paper.abstract).lower()
    matched = [kw for kw in keywords if kw.lower() in text]
    paper.matched_keywords = matched
    paper.keyword_score = len(matched)
    return paper


def merge_sources(arxiv_papers: list[Paper], hf_papers: list[Paper]) -> list[Paper]:
    merged: dict[str, Paper] = {}
    for p in arxiv_papers:
        merged[p.paper_id] = p
    for p in hf_papers:
        if p.paper_id in merged:
            merged[p.paper_id].source = "HuggingFace"
            merged[p.paper_id].hf_upvotes = p.hf_upvotes
        else:
            merged[p.paper_id] = p
    return list(merged.values())


def filter_papers(
    papers: list[Paper],
    keywords: list[str],
    min_score: int = 1,
    hf_always_include: bool = True,
) -> list[Paper]:
    result = []
    for p in papers:
        score_paper(p, keywords)
        if p.source == "HuggingFace" and hf_always_include:
            result.append(p)
        elif p.keyword_score >= min_score:
            result.append(p)

    result.sort(key=lambda p: p.keyword_score, reverse=True)
    logger.info(f"Filter: {len(result)} papers passed (from {len(papers)} total)")
    return result
