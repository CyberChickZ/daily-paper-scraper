#!/usr/bin/env python3
"""Build static GitHub Pages site from Notion database."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from notion_api import NotionAPI
from datetime import datetime


def parse_page(page):
    props = page["properties"]
    def get_text(name):
        parts = props.get(name, {}).get("rich_text", [])
        return "".join(p["plain_text"] for p in parts) if parts else ""
    def get_title():
        parts = props.get("Name", {}).get("title", [])
        return parts[0]["plain_text"] if parts else ""
    def get_select(name):
        sel = props.get(name, {}).get("select")
        return sel["name"] if sel else ""
    def get_multi(name):
        return [o["name"] for o in props.get(name, {}).get("multi_select", [])]
    def get_cb(name):
        return props.get(name, {}).get("checkbox", False)

    return {
        "title": get_title(),
        "authors": get_text("Authors"),
        "summary": get_text("Chinese Summary"),
        "research_line": get_select("Research Line"),
        "evolution_note": get_text("Evolution Note"),
        "keywords": get_multi("Keywords"),
        "date": props.get("Date", {}).get("date", {}).get("start", "") if props.get("Date", {}).get("date") else "",
        "arxiv_url": props.get("arXiv Link", {}).get("url", ""),
        "pdf_url": props.get("PDF Link", {}).get("url", ""),
        "starred": get_cb("Starred"),
        "favorite": get_cb("Favorite"),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daily Papers - Research Knowledge Base</title>
<style>
:root{--bg:#f5f5f4;--card:#fff;--text:#1a1a1a;--dim:#6b7280;--accent:#ff9d00;--blue:#2563eb;--green:#16a34a;--purple:#7c3aed;--border:#e5e7eb;--tag-bg:#f3f4f6;--r:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.hd{background:#fff;border-bottom:1px solid var(--border);padding:16px 0;position:sticky;top:0;z-index:100}
.hd-in{max-width:900px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px}
.logo span{color:var(--accent)}
.stats{font-size:13px;color:var(--dim)}
.updated{font-size:12px;color:var(--dim)}
.fl{max-width:900px;margin:16px auto;padding:0 24px;display:flex;gap:8px;flex-wrap:wrap}
.fb{padding:6px 16px;border-radius:20px;border:1px solid var(--border);background:#fff;font-size:13px;cursor:pointer;transition:all .15s;color:var(--dim)}
.fb:hover{border-color:var(--accent);color:var(--text)}
.fb.on{background:var(--text);color:#fff;border-color:var(--text)}
.pl{max-width:900px;margin:0 auto;padding:0 24px 60px}
.pc{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:20px 24px;margin-bottom:12px;transition:all .15s;position:relative}
.pc:hover{border-color:#d1d5db;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.pt{font-size:16px;font-weight:600;color:var(--text);text-decoration:none;line-height:1.4;display:block}
.pt:hover{color:var(--blue)}
.pm{margin-top:6px;font-size:13px;color:var(--dim)}
.tags{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.tg{padding:2px 10px;border-radius:12px;font-size:12px;font-weight:500}
.tl{color:#fff;font-weight:600}
.tl.bm{background:var(--purple)}.tl.hm{background:var(--blue)}.tl.mp{background:var(--green)}.tl.ot{background:var(--dim)}
.tk{background:var(--tag-bg);color:var(--dim)}
.ps{margin-top:12px;font-size:14px;color:var(--text);white-space:pre-line;line-height:1.7}
.pe{margin-top:8px;font-size:13px;color:var(--purple);font-style:italic}
.lk{margin-top:10px;display:flex;gap:12px}
.lk a{font-size:13px;color:var(--blue);text-decoration:none}
.lk a:hover{text-decoration:underline}
.star::before{content:"\\2B50";position:absolute;top:12px;left:-8px;font-size:14px}
.fav::after{content:"\\2764\\FE0F";position:absolute;top:12px;right:12px;font-size:14px}
.empty{text-align:center;padding:60px;color:var(--dim)}
</style>
</head>
<body>
<div class="hd"><div class="hd-in">
  <div class="logo">📄 <span>Daily Papers</span></div>
  <div><div class="stats" id="stats"></div><div class="updated">Updated: UPDATED_TIME</div></div>
</div></div>
<div class="fl" id="fl">
  <button class="fb on" data-f="all">全部</button>
  <button class="fb" data-f="Body Models">🧬 Body Models</button>
  <button class="fb" data-f="HPE→Mesh">👁️ HPE→Mesh</button>
  <button class="fb" data-f="Motion-Physics">⚡ Motion-Physics</button>
  <button class="fb" data-f="starred">⭐ Starred</button>
  <button class="fb" data-f="favorites">❤️ Favorites</button>
</div>
<div class="pl" id="pl"></div>
<script>
const D=PAPERS_JSON;
let cf='all';
function render(){
  let p=D;
  if(cf==='starred')p=p.filter(x=>x.starred);
  else if(cf==='favorites')p=p.filter(x=>x.favorite);
  else if(cf!=='all')p=p.filter(x=>x.research_line===cf);
  document.getElementById('stats').textContent=p.length+' / '+D.length+' papers';
  if(!p.length){document.getElementById('pl').innerHTML='<div class="empty">暂无论文</div>';return}
  document.getElementById('pl').innerHTML=p.map(card).join('');
}
function card(p){
  const lc={'Body Models':'bm','HPE→Mesh':'hm','Motion-Physics':'mp'}[p.research_line]||'ot';
  const kw=p.keywords.slice(0,4).map(k=>'<span class="tg tk">'+k+'</span>').join('');
  const lt=p.research_line?'<span class="tg tl '+lc+'">'+p.research_line+'</span>':'';
  const s=p.summary||'';
  const sc=p.starred?'star':'';
  const fc=p.favorite?'fav':'';
  return '<div class="pc '+sc+' '+fc+'">'+
    '<a class="pt" href="'+p.arxiv_url+'" target="_blank">'+p.title+'</a>'+
    '<div class="pm">'+p.authors+(p.date?' · '+p.date:'')+'</div>'+
    '<div class="tags">'+lt+kw+'</div>'+
    (s?'<div class="ps">'+s+'</div>':'')+
    (p.evolution_note?'<div class="pe">↗ '+p.evolution_note+'</div>':'')+
    '<div class="lk">'+(p.arxiv_url?'<a href="'+p.arxiv_url+'" target="_blank">arXiv</a>':'')+(p.pdf_url?'<a href="'+p.pdf_url+'" target="_blank">PDF</a>':'')+'</div>'+
    '</div>';
}
document.getElementById('fl').onclick=e=>{
  if(!e.target.classList.contains('fb'))return;
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('on'));
  e.target.classList.add('on');
  cf=e.target.dataset.f;
  render();
};
render();
</script>
</body>
</html>"""


def main():
    api = NotionAPI()
    print("Querying papers from Notion...")
    pages = api.query_database()
    papers = [parse_page(p) for p in pages]
    papers.sort(key=lambda p: p["date"] or "", reverse=True)
    print(f"  {len(papers)} papers loaded")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = HTML_TEMPLATE.replace("PAPERS_JSON", json.dumps(papers, ensure_ascii=False))
    html = html.replace("UPDATED_TIME", now)

    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Built docs/index.html ({len(papers)} papers)")


if __name__ == "__main__":
    main()
