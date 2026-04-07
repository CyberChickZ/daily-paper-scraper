#!/usr/bin/env python3
"""Backfill highlight / chinese_summary / research_line / lab / evolution_note for papers
already in Notion that are missing these fields.

Unlike the daily enrichment (which classifies from title+abstract), this script actually
DOWNLOADS and READS the full PDF of each paper via pymupdf and feeds a real text excerpt
to the LLM. Results are PATCH-ed back to Notion.

Usage:
    # 1. Credentials from .env
    set -a && source .env && set +a
    export LLM_API_KEY=...
    export LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
    export LLM_MODEL=glm-4-flash

    # 2. Dry run (shows what would be updated, no writes)
    python scripts/backfill_enrichment.py --dry-run --limit 3

    # 3. Real run
    python scripts/backfill_enrichment.py --limit 10
    python scripts/backfill_enrichment.py                # full backfill
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    import pymupdf  # noqa: F401
    import pymupdf as fitz
except ImportError:
    try:
        import fitz  # type: ignore
    except ImportError:
        print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
        sys.exit(1)


NOTION_API = "https://api.notion.com/v1"
PDF_CACHE = Path(os.environ.get("DP_PDF_CACHE", "/tmp/dp_pdfs"))
PDF_CACHE.mkdir(parents=True, exist_ok=True)

RESEARCH_LINES = {"Body Models", "HPE→Mesh", "Motion-Physics", "Other"}

PROMPT_TEMPLATE = """You are a research paper classifier for a 3D human body / motion research lab.

Your task: read the provided paper text and produce a structured analysis. Do NOT guess from the title alone — base every answer on concrete details from the text.

RESEARCH LINES:
- Body Models: SMPL / SMPL-X / MANO / FLAME, parametric body, neural implicit body, body shape modeling
- HPE→Mesh: image or video → 3D human pose and mesh recovery (HMR family, pose estimation)
- Motion-Physics: motion generation, physics-based character animation, motion diffusion, RL motion control
- Other: only weakly related or unrelated to 3D humans / motion

TITLE: {title}
AUTHORS: {authors}

PAPER TEXT (may be truncated):
\"\"\"
{text}
\"\"\"

Output ONLY a JSON object, no markdown, no commentary:
{{
  "research_line": "Body Models" | "HPE→Mesh" | "Motion-Physics" | "Other",
  "highlight": "2-3 English sentences. State the concrete novel contribution and the key technical idea. Reference specific components from the text. No marketing fluff.",
  "lab": "Primary lab/institution in short form (Meta FAIR, CMU, ETH Zurich, Google DeepMind, MPI, Stanford, Tsinghua, PKU, ...). Empty string if the text has no affiliation.",
  "chinese_summary": "纯文本四行，每行以固定前缀：\\n中文标题: ...\\n核心贡献: 1-2句，基于原文具体说明做了什么\\n基于什么改进: 前人工作(具体方法名) + 本文的创新点\\n关键结果: 定量数字或定性突破(从原文摘录)",
  "evolution_note": "一句话: = [前序方法] + [本文创新]，留空字符串如果原文没有明确前序"
}}"""


# ---------------- Notion helpers ----------------

def notion_req(method: str, path: str, body=None, token: str = ""):
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")[:300]
            print(f"    Notion HTTP {e.code}: {body_text}", file=sys.stderr)
            if e.code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception as e:
            print(f"    Notion error: {e}", file=sys.stderr)
            time.sleep(1)
    raise RuntimeError(f"Notion request failed: {method} {path}")


def get_text(prop: dict) -> str:
    parts = prop.get("rich_text", []) if prop else []
    return "".join(x.get("plain_text", "") for x in parts)


def query_all_pages(token: str, db_id: str) -> list[dict]:
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion_req("POST", f"databases/{db_id}/query", body, token)
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return pages


def needs_enrichment(page: dict) -> bool:
    props = page["properties"]
    highlight = get_text(props.get("Highlight", {}))
    summary = get_text(props.get("Chinese Summary", {}))
    rl = (props.get("Research Line", {}).get("select") or {}).get("name", "")
    # Consider it missing if any of the three core fields is empty
    return not (highlight.strip() and summary.strip() and rl.strip())


def split_rich_text(text: str, limit: int = 2000) -> list[dict]:
    text = text or ""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    chunks = []
    for i in range(0, len(text), limit):
        chunks.append({"type": "text", "text": {"content": text[i : i + limit]}})
    return chunks


def patch_page(token: str, page_id: str, enrichment: dict, existing: dict, force: bool = False) -> list[str]:
    """PATCH only the fields that are currently empty on the page (unless force=True).

    Returns the list of field names that were actually updated.
    """
    properties = {}
    updated = []

    text_fields = [
        ("Highlight", "highlight"),
        ("Chinese Summary", "chinese_summary"),
        ("Lab", "lab"),
        ("Evolution Note", "evolution_note"),
    ]
    for notion_key, enrich_key in text_fields:
        new_val = (enrichment.get(enrich_key) or "").strip()
        if not new_val:
            continue
        if force or not (existing.get(enrich_key) or "").strip():
            properties[notion_key] = {"rich_text": split_rich_text(new_val)}
            updated.append(notion_key)

    rl = enrichment.get("research_line", "").strip()
    if rl in RESEARCH_LINES:
        if force or not (existing.get("research_line") or "").strip():
            properties["Research Line"] = {"select": {"name": rl}}
            updated.append("Research Line")

    if properties:
        notion_req("PATCH", f"pages/{page_id}", {"properties": properties}, token)
    return updated


# ---------------- PDF helpers ----------------

def extract_arxiv_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w\.\-/]+?)(?:v\d+)?(?:\.pdf)?$", url)
    return m.group(1) if m else ""


def download_pdf(arxiv_id: str) -> Path | None:
    if not arxiv_id:
        return None
    cache_path = PDF_CACHE / f"{arxiv_id.replace('/', '_')}.pdf"
    if cache_path.exists() and cache_path.stat().st_size > 1024:
        return cache_path
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "daily-paper-scraper/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
        if len(content) < 1024:
            return None
        cache_path.write_bytes(content)
        return cache_path
    except Exception as e:
        print(f"    PDF download failed for {arxiv_id}: {e}", file=sys.stderr)
        return None


def extract_text(pdf_path: Path, max_chars: int = 12000) -> str:
    """Extract readable text from the paper. Grab first pages + last page (intro + conclusion).

    The goal is to give the LLM the most informative chunks while keeping token cost low.
    """
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"    PDF parse failed: {e}", file=sys.stderr)
        return ""
    try:
        pages = doc.page_count
        # Grab all text from first min(6, pages) pages + last page
        indices = list(range(min(6, pages)))
        if pages > 7:
            indices.append(pages - 1)
        parts = []
        for i in indices:
            try:
                page = doc.load_page(i)
                parts.append(page.get_text("text"))
            except Exception:
                continue
        text = "\n".join(parts)
    finally:
        doc.close()
    # Clean up: collapse runs of whitespace, drop lines that look like pure numerals (page numbers, line refs)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    if len(text) > max_chars:
        # Keep the beginning (usually abstract/intro/method) and the tail (usually conclusion/results)
        head = text[: int(max_chars * 0.75)]
        tail = text[-int(max_chars * 0.25) :]
        text = head + "\n...\n" + tail
    return text.strip()


# ---------------- LLM helpers ----------------

def llm_call(prompt: str, api_key: str, base_url: str, model: str, timeout: int = 90) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def parse_enrichment(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in response")
    obj = json.loads(raw[start : end + 1])
    rl = str(obj.get("research_line") or "").strip()
    if rl not in RESEARCH_LINES:
        rl = "Other"
    return {
        "research_line": rl,
        "highlight": str(obj.get("highlight") or "").strip(),
        "lab": str(obj.get("lab") or "").strip(),
        "chinese_summary": str(obj.get("chinese_summary") or "").strip(),
        "evolution_note": str(obj.get("evolution_note") or "").strip(),
    }


def enrich_from_text(title: str, authors: str, text: str,
                     api_key: str, base_url: str, model: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        title=title[:500],
        authors=authors[:500],
        text=text[:12000],
    )
    for attempt in range(3):
        try:
            raw = llm_call(prompt, api_key, base_url, model)
            return parse_enrichment(raw)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:200]
            print(f"    LLM HTTP {e.code} (attempt {attempt+1}/3): {err_body}", file=sys.stderr)
            if e.code == 429:
                time.sleep(3 * (attempt + 1))
            else:
                time.sleep(1)
        except Exception as e:
            print(f"    LLM error (attempt {attempt+1}/3): {e}", file=sys.stderr)
            time.sleep(1)
    raise RuntimeError("LLM enrichment failed after 3 attempts")


# ---------------- Main ----------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Only process first N papers (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Notion, print enrichment only")
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between LLM calls")
    parser.add_argument("--only-read", action="store_true",
                        help="Also include pages already marked as Read (default: skip Read ones)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing non-empty fields (default: only fill empty ones)")
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN", "")
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    model = os.environ.get("LLM_MODEL", "glm-4-flash")
    if not (token and db_id):
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID are required", file=sys.stderr)
        sys.exit(1)
    if not api_key:
        print("ERROR: LLM_API_KEY is required", file=sys.stderr)
        sys.exit(1)

    print(f"Querying Notion database {db_id[:8]}...")
    pages = query_all_pages(token, db_id)
    print(f"  {len(pages)} total pages")

    todo = []
    for page in pages:
        if not needs_enrichment(page):
            continue
        props = page["properties"]
        is_read = props.get("Read", {}).get("checkbox", False)
        if is_read and not args.only_read:
            continue
        title_parts = props.get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        authors = get_text(props.get("Authors", {}))
        arxiv_url = props.get("arXiv Link", {}).get("url", "") or ""
        existing = {
            "highlight": get_text(props.get("Highlight", {})),
            "chinese_summary": get_text(props.get("Chinese Summary", {})),
            "lab": get_text(props.get("Lab", {})),
            "evolution_note": get_text(props.get("Evolution Note", {})),
            "research_line": (props.get("Research Line", {}).get("select") or {}).get("name", ""),
        }
        todo.append({
            "id": page["id"],
            "title": title,
            "authors": authors,
            "arxiv_url": arxiv_url,
            "existing": existing,
        })

    print(f"  {len(todo)} need enrichment")
    if args.limit > 0:
        todo = todo[: args.limit]
        print(f"  limited to first {args.limit}")

    ok, skipped, failed = 0, 0, 0
    for n, paper in enumerate(todo, 1):
        print(f"\n[{n}/{len(todo)}] {paper['title'][:80]}")
        arxiv_id = extract_arxiv_id(paper["arxiv_url"])
        if not arxiv_id:
            print(f"    SKIP: no arxiv id in URL {paper['arxiv_url']!r}")
            skipped += 1
            continue
        print(f"    arxiv={arxiv_id}")

        pdf_path = download_pdf(arxiv_id)
        if not pdf_path:
            skipped += 1
            continue

        text = extract_text(pdf_path)
        if len(text) < 500:
            print(f"    SKIP: extracted text too short ({len(text)} chars)")
            skipped += 1
            continue
        print(f"    text: {len(text)} chars")

        try:
            enrichment = enrich_from_text(
                paper["title"], paper["authors"], text, api_key, base_url, model
            )
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
            failed += 1
            continue

        print(f"    -> {enrichment['research_line']} | lab={enrichment['lab'][:40]}")
        print(f"       highlight: {enrichment['highlight'][:120]}...")

        if args.dry_run:
            # Preview which fields WOULD be updated
            would_update = []
            for notion_key, enrich_key in [
                ("Highlight", "highlight"), ("Chinese Summary", "chinese_summary"),
                ("Lab", "lab"), ("Evolution Note", "evolution_note"),
            ]:
                if (enrichment.get(enrich_key) or "").strip() and (
                    args.force or not (paper["existing"].get(enrich_key) or "").strip()
                ):
                    would_update.append(notion_key)
            if enrichment.get("research_line", "").strip() in RESEARCH_LINES and (
                args.force or not paper["existing"].get("research_line")
            ):
                would_update.append("Research Line")
            print(f"       [dry-run] would update: {would_update or '(nothing, all fields already set)'}")
            ok += 1
        else:
            try:
                updated = patch_page(token, paper["id"], enrichment, paper["existing"], force=args.force)
            except Exception as e:
                print(f"    Notion PATCH failed: {e}", file=sys.stderr)
                failed += 1
                continue
            if updated:
                print(f"       patched: {updated}")
                ok += 1
            else:
                print(f"       nothing to patch (all fields already set)")
                skipped += 1
        time.sleep(args.sleep)

    print(f"\nDone: {ok} enriched, {skipped} skipped, {failed} failed, out of {len(todo)}")


if __name__ == "__main__":
    main()
