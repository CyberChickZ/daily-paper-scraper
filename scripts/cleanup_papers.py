#!/usr/bin/env python3
"""Classify papers by research line and archive irrelevant ones."""
import json
import argparse
import os
from notion_api import NotionAPI

# Research line keyword sets (must match in title or abstract)
LINE1_KEYWORDS = [
    "body model", "parametric body", "SMPL", "MANO", "FLAME", "SMPL-X", "STAR body",
    "body template", "blend shapes", "skinning", "body mesh", "body shape space",
    "body representation", "neural body", "implicit body", "volumetric body",
    "body prior", "expressive body", "articulated body",
]
LINE2_KEYWORDS = [
    "mesh recovery", "HMR", "human mesh", "pose estimation",
    "3D pose", "body reconstruction", "shape estimation", "pose regression",
    "lifting", "heatmap pose", "body fitting", "SMPLify", "SPIN",
    "human reconstruction", "whole-body reconstruction",
]
LINE3_KEYWORDS = [
    "motion generation", "motion synthesis", "motion diffusion", "motion prior",
    "character animation", "character control", "motion capture",
    "motion policy", "motion imitation", "adversarial motion",
    "physics-based character", "physics-based humanoid", "physically plausible human",
    "motion matching", "deepmimic", "motion tracking humanoid",
    "text-to-motion", "motion latent",
]
IRRELEVANT_SIGNALS = [
    "robot locomotion", "robot manipulation", "autonomous driving",
    "activity recognition", "action recognition", "sign language",
    "medical imaging", "clinical", "patholog", "animal motion",
    "grasping", "navigation", "point cloud segmentation", "object detection",
    "image generation", "text-to-image", "image editing",
    "scene generation", "3D scene", "room layout",
    "speech", "audio", "music",
]


def classify_paper(title, abstract):
    text = (title + " " + abstract).lower()

    # Check irrelevant signals first
    neg_score = sum(1 for kw in IRRELEVANT_SIGNALS if kw.lower() in text)

    scores = {
        "Body Models": sum(1 for kw in LINE1_KEYWORDS if kw.lower() in text),
        "HPE→Mesh": sum(1 for kw in LINE2_KEYWORDS if kw.lower() in text),
        "Motion-Physics": sum(1 for kw in LINE3_KEYWORDS if kw.lower() in text),
    }

    best_line = max(scores, key=scores.get)
    best_score = scores[best_line]

    if neg_score > best_score and best_score < 2:
        return "irrelevant", 0
    if best_score >= 2:
        return best_line, best_score
    if best_score == 1:
        return "Other", 1
    return "irrelevant", 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only classify, don't archive")
    args = parser.parse_args()

    api = NotionAPI()
    print("Querying all papers...")
    pages = api.query_database()
    print(f"Found {len(pages)} papers")

    results = {"Body Models": [], "HPE→Mesh": [], "Motion-Physics": [], "Other": [], "irrelevant": []}
    ignore_ids = []

    for page in pages:
        title_parts = page["properties"].get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""

        abstract_parts = page["properties"].get("Abstract", {}).get("rich_text", [])
        abstract = abstract_parts[0]["plain_text"][:500] if abstract_parts else ""

        # Skip already classified papers (seminal papers from seed)
        existing_line = page["properties"].get("Research Line", {}).get("select")
        if existing_line:
            results[existing_line["name"]].append(title)
            continue

        classification, score = classify_paper(title, abstract)
        results[classification].append(title)

        if args.dry_run:
            if classification == "irrelevant":
                print(f"  [ARCHIVE] {title[:80]}")
            else:
                print(f"  [{classification}] (score={score}) {title[:80]}")
        else:
            if classification == "irrelevant":
                api.archive_page(page["id"])
                arxiv_url = page["properties"].get("arXiv Link", {}).get("url", "")
                pid = arxiv_url.rstrip("/").split("/")[-1] if arxiv_url else ""
                if pid:
                    ignore_ids.append(pid)
            elif classification == "Other":
                api.archive_page(page["id"])
                arxiv_url = page["properties"].get("arXiv Link", {}).get("url", "")
                pid = arxiv_url.rstrip("/").split("/")[-1] if arxiv_url else ""
                if pid:
                    ignore_ids.append(pid)
            else:
                api.update_page(page["id"], {
                    "Research Line": {"select": {"name": classification}},
                })

    # Print summary
    print(f"\n--- Classification Summary ---")
    for cat, papers in results.items():
        print(f"  {cat}: {len(papers)} papers")

    if not args.dry_run and ignore_ids:
        os.makedirs("data", exist_ok=True)
        with open("data/ignore_list.json", "w") as f:
            json.dump({"ignored_paper_ids": ignore_ids}, f, indent=2)
        print(f"\nWrote {len(ignore_ids)} IDs to data/ignore_list.json")
        print(f"Archived {len(results['irrelevant'])} papers from Notion")


if __name__ == "__main__":
    main()
