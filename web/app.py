#!/usr/bin/env python3
"""HuggingFace-style paper browser — local web app backed by Notion."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from flask import Flask, render_template, jsonify, request
from notion_api import NotionAPI

app = Flask(__name__)
api = NotionAPI(config_path=os.path.join(os.path.dirname(__file__), '..', 'config.yaml'))


def parse_page(page):
    props = page["properties"]
    def get_text(prop_name):
        parts = props.get(prop_name, {}).get("rich_text", [])
        return parts[0]["plain_text"] if parts else ""
    def get_title():
        parts = props.get("Name", {}).get("title", [])
        return parts[0]["plain_text"] if parts else ""
    def get_select(prop_name):
        sel = props.get(prop_name, {}).get("select")
        return sel["name"] if sel else ""
    def get_multi(prop_name):
        return [o["name"] for o in props.get(prop_name, {}).get("multi_select", [])]
    def get_checkbox(prop_name):
        return props.get(prop_name, {}).get("checkbox", False)

    return {
        "id": page["id"],
        "title": get_title(),
        "authors": get_text("Authors"),
        "summary": get_text("Chinese Summary"),
        "abstract": get_text("Abstract")[:300],
        "research_line": get_select("Research Line"),
        "reading_status": get_select("Reading Status"),
        "evolution_note": get_text("Evolution Note"),
        "keywords": get_multi("Keywords"),
        "categories": get_multi("Categories"),
        "date": props.get("Date", {}).get("date", {}).get("start", "") if props.get("Date", {}).get("date") else "",
        "arxiv_url": props.get("arXiv Link", {}).get("url", ""),
        "pdf_url": props.get("PDF Link", {}).get("url", ""),
        "starred": get_checkbox("Starred"),
        "followed": get_checkbox("Followed"),
        "favorite": get_checkbox("Favorite"),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/papers")
def get_papers():
    line = request.args.get("line", "")
    pages = api.query_database()
    papers = [parse_page(p) for p in pages]
    if line and line != "all":
        papers = [p for p in papers if p["research_line"] == line]
    papers.sort(key=lambda p: p["date"] or "", reverse=True)
    return jsonify(papers)


@app.route("/api/toggle", methods=["POST"])
def toggle_prop():
    data = request.json
    page_id = data["page_id"]
    prop = data["property"]  # "Followed" or "Favorite"
    value = data["value"]
    api.update_page(page_id, {prop: {"checkbox": value}})
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5555)
