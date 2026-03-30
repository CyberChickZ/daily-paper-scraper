"""Extract dynamic keywords from Focus papers in Notion for follow-up tracking."""
from __future__ import annotations
import os
import re
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"


def _notion_req(token, method, path, body=None):
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read())


def get_focus_papers(token: str, db_id: str) -> list[dict]:
    """Fetch papers with Focus=true from Notion."""
    body = {
        "page_size": 100,
        "filter": {"property": "Focus", "checkbox": {"equals": True}},
    }
    try:
        data = _notion_req(token, "POST", f"databases/{db_id}/query", body)
    except Exception as e:
        logger.warning(f"Failed to fetch focus papers: {e}")
        return []

    papers = []
    for page in data.get("results", []):
        p = page["properties"]
        title_parts = p.get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        authors_parts = p.get("Authors", {}).get("rich_text", [])
        authors = "".join(x["plain_text"] for x in authors_parts) if authors_parts else ""
        lab_parts = p.get("Lab", {}).get("rich_text", [])
        lab = "".join(x["plain_text"] for x in lab_parts) if lab_parts else ""
        papers.append({"title": title, "authors": authors, "lab": lab})
    return papers


def extract_dynamic_keywords(focus_papers: list[dict]) -> list[str]:
    """Extract method names and key author surnames from focus papers."""
    keywords = set()

    for paper in focus_papers:
        title = paper["title"]

        # Extract acronyms/method names from title (e.g., "GVHMR", "VGGT", "PhysPT")
        # Pattern: ALL-CAPS (2+) or CamelCase starting with uppercase
        acronyms = re.findall(r'\b[A-Z]{2,}[0-9]*\b', title)  # strict: SMPL, VGGT, HMR
        camel = re.findall(r'\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b', title)  # PhysPT, DeepMimic
        for a in acronyms + camel:
            # Skip common words and short acronyms
            if a.lower() not in {"the", "for", "and", "with", "from", "via", "how",
                                  "new", "learning", "towards", "using", "based",
                                  "human", "model", "models", "motion", "body",
                                  "neural", "deep", "real", "time", "end", "large",
                                  "scale", "multi", "person", "single", "image",
                                  "video", "pose", "shape", "mesh", "physics",
                                  "adversarial", "priors", "control", "tracking",
                                  "recovering", "skinned", "linear", "stylized",
                                  "character", "guided", "example", "reinforcement",
                                  "reconstructing", "humans", "transformers"}:
                keywords.add(a)

        # Extract first author surname (most likely to publish follow-ups)
        authors = paper["authors"]
        if authors:
            first_author = authors.split(",")[0].strip()
            parts = first_author.split()
            if parts:
                surname = parts[-1]
                if len(surname) > 2:  # skip initials
                    keywords.add(f'au:"{surname}"')

        # Extract lab name if available
        lab = paper.get("lab", "")
        if lab and len(lab) > 2:
            keywords.add(f'"{lab}"')

    logger.info(f"Focus tracker: {len(focus_papers)} focus papers → {len(keywords)} dynamic keywords")
    if keywords:
        logger.info(f"  Dynamic keywords: {sorted(keywords)}")
    return list(keywords)
