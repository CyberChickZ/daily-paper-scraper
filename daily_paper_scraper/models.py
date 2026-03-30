from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
import json


@dataclass
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_date: str  # ISO format string
    arxiv_url: str
    pdf_url: str
    source: str  # "arXiv" or "HuggingFace"
    matched_keywords: list[str] = field(default_factory=list)
    keyword_score: int = 0
    chinese_summary: str = ""
    highlight: str = ""
    lab: str = ""
    research_line: str = ""
    evolution_note: str = ""
    hf_upvotes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Paper:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def papers_to_json(papers: list[Paper], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([p.to_dict() for p in papers], f, ensure_ascii=False, indent=2)


def papers_from_json(path: str) -> list[Paper]:
    with open(path, "r", encoding="utf-8") as f:
        return [Paper.from_dict(d) for d in json.load(f)]
