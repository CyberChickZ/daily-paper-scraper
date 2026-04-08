from __future__ import annotations
import logging
import re

from daily_paper_scraper.models import Paper

logger = logging.getLogger(__name__)


_KEYWORD_RE_CACHE: dict[str, re.Pattern] = {}


def _kw_pattern(kw: str) -> re.Pattern:
    """Compile a keyword into a word-boundary regex (case-insensitive).

    Multi-word phrases ("human pose") still match across whitespace, but a
    single token like "SKEL" will NOT match inside "skeleton" or "skeletal".
    """
    cached = _KEYWORD_RE_CACHE.get(kw)
    if cached is not None:
        return cached
    parts = re.split(r"\s+", kw.strip())
    body = r"\s+".join(re.escape(p) for p in parts)
    # \b only works around word characters; for keywords ending in punctuation
    # (e.g. "SMPL-X") fall back to a non-word lookahead.
    pattern = rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])"
    compiled = re.compile(pattern, re.IGNORECASE)
    _KEYWORD_RE_CACHE[kw] = compiled
    return compiled


def score_paper(paper: Paper, keywords: list[str]) -> Paper:
    text = paper.title + " " + paper.abstract
    matched = [kw for kw in keywords if _kw_pattern(kw).search(text)]
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
