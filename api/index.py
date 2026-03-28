"""Vercel serverless function — serves the paper browser with live Notion data."""
import os, sys, json, time

# Ensure api/ directory is on path for notion_api import
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, Response
from notion_api import NotionAPI

app = Flask(__name__)


def get_api():
    token = os.environ.get("NOTION_TOKEN", "")
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    api = NotionAPI.__new__(NotionAPI)
    api.headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    api.db_id = db_id
    api._last_call = 0
    return api


def parse_page(page):
    props = page["properties"]
    def gt(n):
        parts = props.get(n, {}).get("rich_text", [])
        return "".join(p["plain_text"] for p in parts) if parts else ""
    def gs(n):
        sel = props.get(n, {}).get("select")
        return sel["name"] if sel else ""
    def gm(n):
        return [o["name"] for o in props.get(n, {}).get("multi_select", [])]
    def gc(n):
        return props.get(n, {}).get("checkbox", False)
    title_parts = props.get("Name", {}).get("title", [])
    title = title_parts[0]["plain_text"] if title_parts else ""
    d = props.get("Date", {}).get("date")
    return {
        "id": page["id"], "title": title, "authors": gt("Authors"),
        "summary": gt("Chinese Summary"), "research_line": gs("Research Line"),
        "evolution_note": gt("Evolution Note"), "keywords": gm("Keywords"),
        "date": d["start"] if d else "",
        "arxiv_url": props.get("arXiv Link", {}).get("url", ""),
        "pdf_url": props.get("PDF Link", {}).get("url", ""),
        "starred": gc("Starred"), "followed": gc("Followed"), "favorite": gc("Favorite"),
    }


HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daily Papers</title>
<style>
:root{--bg:#f5f5f4;--card:#fff;--text:#1a1a1a;--dim:#6b7280;--accent:#ff9d00;--blue:#2563eb;--green:#16a34a;--purple:#7c3aed;--red:#dc2626;--border:#e5e7eb;--tag-bg:#f3f4f6;--r:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.hd{background:#fff;border-bottom:1px solid var(--border);padding:16px 0;position:sticky;top:0;z-index:100}
.hi{max-width:900px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px}
.logo span{color:var(--accent)}
.st{font-size:13px;color:var(--dim)}
.fl{max-width:900px;margin:16px auto;padding:0 24px;display:flex;gap:8px;flex-wrap:wrap}
.fb{padding:6px 16px;border-radius:20px;border:1px solid var(--border);background:#fff;font-size:13px;cursor:pointer;transition:all .15s;color:var(--dim)}
.fb:hover{border-color:var(--accent);color:var(--text)}.fb.on{background:var(--text);color:#fff;border-color:var(--text)}
.pl{max-width:900px;margin:0 auto;padding:0 24px 60px}
.pc{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:20px 24px;margin-bottom:12px;transition:all .15s}
.pc:hover{border-color:#d1d5db;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.ph{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.pt{font-size:16px;font-weight:600;color:var(--text);text-decoration:none;line-height:1.4;flex:1}
.pt:hover{color:var(--blue)}
.pa{display:flex;gap:4px;flex-shrink:0}
.ab{width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:15px;transition:all .15s}
.ab:hover{background:var(--tag-bg)}.ab.on{background:var(--accent);border-color:var(--accent)}.ab.fv{background:var(--red);border-color:var(--red)}
.pm{margin-top:6px;font-size:13px;color:var(--dim)}
.tags{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.tg{padding:2px 10px;border-radius:12px;font-size:12px;font-weight:500}
.tl{color:#fff;font-weight:600}.tl.bm{background:var(--purple)}.tl.hm{background:var(--blue)}.tl.mp{background:var(--green)}.tl.ot{background:var(--dim)}
.tk{background:var(--tag-bg);color:var(--dim)}
.ps{margin-top:12px;font-size:14px;color:var(--text);white-space:pre-line;line-height:1.7}
.pe{margin-top:8px;font-size:13px;color:var(--purple);font-style:italic}
.lk{margin-top:10px;display:flex;gap:12px}.lk a{font-size:13px;color:var(--blue);text-decoration:none}.lk a:hover{text-decoration:underline}
.ld{text-align:center;padding:60px;color:var(--dim)}
</style>
</head>
<body>
<div class="hd"><div class="hi">
<div class="logo">📄 <span>Daily Papers</span></div>
<div class="st" id="st">Loading...</div>
</div></div>
<div class="fl" id="fl">
<button class="fb on" data-f="all">全部</button>
<button class="fb" data-f="Body Models">🧬 Body Models</button>
<button class="fb" data-f="HPE→Mesh">👁️ HPE→Mesh</button>
<button class="fb" data-f="Motion-Physics">⚡ Motion-Physics</button>
<button class="fb" data-f="followed">📌 待读</button>
<button class="fb" data-f="favorites">❤️ 收藏</button>
</div>
<div class="pl" id="pl"><div class="ld">加载中...</div></div>
<script>
let D=[],cf='all';
async function load(){
  const r=await fetch('/api/papers');D=await r.json();render();
}
function render(){
  let p=D;
  if(cf==='followed')p=p.filter(x=>x.followed);
  else if(cf==='favorites')p=p.filter(x=>x.favorite);
  else if(cf!=='all')p=p.filter(x=>x.research_line===cf);
  document.getElementById('st').textContent=p.length+' / '+D.length+' papers';
  if(!p.length){document.getElementById('pl').innerHTML='<div class="ld">暂无论文</div>';return}
  document.getElementById('pl').innerHTML=p.map(card).join('');
}
function card(p){
  const lc={'Body Models':'bm','HPE→Mesh':'hm','Motion-Physics':'mp'}[p.research_line]||'ot';
  const kw=p.keywords.slice(0,4).map(k=>`<span class="tg tk">${k}</span>`).join('');
  const lt=p.research_line?`<span class="tg tl ${lc}">${p.research_line}</span>`:'';
  return `<div class="pc">
  <div class="ph">
    <a class="pt" href="${p.arxiv_url}" target="_blank">${p.title}</a>
    <div class="pa">
      <button class="ab ${p.followed?'on':''}" onclick="tog('${p.id}','Followed',${!p.followed},this,'on')" title="关注/待读">📌</button>
      <button class="ab ${p.favorite?'fv':''}" onclick="tog('${p.id}','Favorite',${!p.favorite},this,'fv')" title="收藏">❤️</button>
    </div>
  </div>
  <div class="pm">${p.authors}${p.date?' · '+p.date:''}</div>
  <div class="tags">${lt}${kw}</div>
  ${p.summary?`<div class="ps">${p.summary}</div>`:''}
  ${p.evolution_note?`<div class="pe">↗ ${p.evolution_note}</div>`:''}
  <div class="lk">${p.arxiv_url?`<a href="${p.arxiv_url}" target="_blank">arXiv</a>`:''}${p.pdf_url?`<a href="${p.pdf_url}" target="_blank">PDF</a>`:''}</div>
  </div>`;
}
async function tog(id,prop,val,btn,cls){
  const paper=D.find(x=>x.id===id);
  if(paper){if(prop==='Followed')paper.followed=val;if(prop==='Favorite')paper.favorite=val;}
  btn.classList.toggle(cls,val);
  await fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page_id:id,property:prop,value:val})});
}
document.getElementById('fl').onclick=e=>{
  if(!e.target.classList.contains('fb'))return;
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('on'));
  e.target.classList.add('on');cf=e.target.dataset.f;render();
};
load();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return Response(HTML, content_type="text/html")


@app.route("/api/papers")
def papers():
    api = get_api()
    pages = api.query_database()
    data = [parse_page(p) for p in pages]
    data.sort(key=lambda p: p["date"] or "", reverse=True)
    return jsonify(data)


@app.route("/api/toggle", methods=["POST"])
def toggle():
    d = request.json
    api = get_api()
    api.update_page(d["page_id"], {d["property"]: {"checkbox": d["value"]}})
    return jsonify({"ok": True})
