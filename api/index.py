"""Vercel Python serverless function — native handler, no Flask."""
import os
import json
import time
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error


NOTION_API = "https://api.notion.com/v1"


def notion_req(method, path, body=None):
    token = os.environ.get("NOTION_TOKEN", "")
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt < 2:
                time.sleep(1)
            else:
                raise


def get_papers():
    db_id = os.environ.get("NOTION_DATABASE_ID", "")
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion_req("POST", f"databases/{db_id}/query", body)
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]

    result = []
    for page in pages:
        p = page["properties"]
        def gt(n):
            parts = p.get(n, {}).get("rich_text", [])
            return "".join(x["plain_text"] for x in parts) if parts else ""
        def gs(n):
            s = p.get(n, {}).get("select")
            return s["name"] if s else ""
        def gm(n):
            return [o["name"] for o in p.get(n, {}).get("multi_select", [])]
        def gc(n):
            return p.get(n, {}).get("checkbox", False)
        title_parts = p.get("Name", {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else ""
        d = p.get("Date", {}).get("date")
        result.append({
            "id": page["id"], "title": title, "authors": gt("Authors"),
            "summary": gt("Chinese Summary"), "research_line": gs("Research Line"),
            "evolution_note": gt("Evolution Note"), "keywords": gm("Keywords"),
            "date": d["start"] if d else "",
            "arxiv_url": p.get("arXiv Link", {}).get("url", ""),
            "pdf_url": p.get("PDF Link", {}).get("url", ""),
            "read": gc("Read"), "focus": gc("Focus"),
        })
    result.sort(key=lambda x: x["date"] or "", reverse=True)
    return result


HTML = """<!DOCTYPE html>
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
.pl{max-width:900px;margin:0 auto;padding:0 24px 80px}
.pc{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:20px 24px;margin-bottom:12px;transition:all .4s ease}
.pc:hover{border-color:#d1d5db;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.pc.fade-out{opacity:0;transform:translateX(60px);max-height:0;padding:0 24px;margin-bottom:0;overflow:hidden}
.ph{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.pt{font-size:16px;font-weight:600;color:var(--text);text-decoration:none;line-height:1.4;flex:1}
.pt:hover{color:var(--blue)}
.pa{display:flex;gap:4px;flex-shrink:0}
.ab{width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:15px;transition:all .15s}
.ab:hover{background:var(--tag-bg)}.ab.on{background:var(--green);border-color:var(--green)}.ab.fv{background:var(--blue);border-color:var(--blue)}
.pm{margin-top:6px;font-size:13px;color:var(--dim)}
.tags{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap}
.tg{padding:2px 10px;border-radius:12px;font-size:12px;font-weight:500}
.tl{color:#fff;font-weight:600}.tl.bm{background:var(--purple)}.tl.hm{background:var(--blue)}.tl.mp{background:var(--green)}.tl.ot{background:var(--dim)}
.tk{background:var(--tag-bg);color:var(--dim)}
.ps{margin-top:12px;font-size:14px;color:var(--text);white-space:pre-line;line-height:1.7}
.pe{margin-top:8px;font-size:13px;color:var(--purple);font-style:italic}
.lk{margin-top:10px;display:flex;gap:12px}.lk a{font-size:13px;color:var(--blue);text-decoration:none}.lk a:hover{text-decoration:underline}
.ld{text-align:center;padding:60px;color:var(--dim)}
.undo-fab{position:fixed;bottom:28px;right:28px;width:56px;height:56px;border-radius:50%;background:var(--text);color:#fff;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);z-index:200;display:none;align-items:center;justify-content:center;font-size:22px;transition:transform .2s ease,box-shadow .2s ease}
.undo-fab:hover{transform:scale(1.1);box-shadow:0 6px 24px rgba(0,0,0,.35)}
.undo-fab.show{display:flex}
.undo-fab .badge{position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;font-size:11px;font-weight:700;min-width:20px;height:20px;border-radius:10px;display:flex;align-items:center;justify-content:center;padding:0 5px}
</style>
</head>
<body>
<div class="hd"><div class="hi">
<div class="logo">&#128196; <span>Daily Papers</span></div>
<div class="st" id="st">Loading...</div>
</div></div>
<div class="fl" id="fl">
<button class="fb on" data-f="all">All</button>
<button class="fb" data-f="Body Models">Body Models</button>
<button class="fb" data-f="HPE&#8594;Mesh">HPE-Mesh</button>
<button class="fb" data-f="Motion-Physics">Motion-Physics</button>
<button class="fb" data-f="read">&#128214; 已读</button>
<button class="fb" data-f="focus">&#128269; 关注</button>
</div>
<div class="pl" id="pl"><div class="ld">Loading...</div></div>
<button class="undo-fab" id="undo-fab" onclick="doUndo()" title="Undo last read">&#8630;<span class="badge" id="undo-badge">0</span></button>
<script>
let D=[],cf='all',undoStack=[];
async function load(){const r=await fetch('/api/papers');D=await r.json();render();}
function render(){
let p=D;
if(cf==='all')p=p.filter(x=>!x.read);
else if(cf==='read')p=p.filter(x=>x.read);
else if(cf==='focus')p=p.filter(x=>x.focus);
else p=p.filter(x=>x.research_line===cf&&!x.read);
const total=D.filter(x=>!x.read).length;
const readCount=D.filter(x=>x.read).length;
document.getElementById('st').textContent=cf==='read'?readCount+' read':p.length+' unread / '+D.length+' total';
if(!p.length){document.getElementById('pl').innerHTML='<div class="ld">'+(cf==='read'?'No read papers yet':'No papers')+'</div>';return;}
document.getElementById('pl').innerHTML=p.map(card).join('');
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function card(p){
const lc={'Body Models':'bm','HPE\\u2192Mesh':'hm','Motion-Physics':'mp'}[p.research_line]||'ot';
const kw=p.keywords.slice(0,4).map(k=>'<span class="tg tk">'+esc(k)+'</span>').join('');
const lt=p.research_line?'<span class="tg tl '+lc+'">'+esc(p.research_line)+'</span>':'';
return '<div class="pc" id="card-'+p.id+'">'+
'<div class="ph">'+
'<a class="pt" href="'+esc(p.arxiv_url)+'" target="_blank">'+esc(p.title)+'</a>'+
'<div class="pa">'+
(p.read?
'<button class="ab" onclick="markUnread(\\''+p.id+'\\',this)" title="Mark unread">&#128194;</button>':
'<button class="ab" onclick="markRead(\\''+p.id+'\\',this)" title="Mark read">&#9989;</button>')+
'<button class="ab '+(p.focus?'fv':'')+'" onclick="togFocus(\\''+p.id+'\\','+(!p.focus)+',this)" title="Focus">&#128269;</button>'+
'</div></div>'+
'<div class="pm">'+esc(p.authors)+(p.date?' &middot; '+p.date:'')+'</div>'+
'<div class="tags">'+lt+kw+'</div>'+
(p.summary?'<div class="ps">'+esc(p.summary)+'</div>':'')+
(p.evolution_note?'<div class="pe">&nearr; '+esc(p.evolution_note)+'</div>':'')+
'<div class="lk">'+(p.arxiv_url?'<a href="'+esc(p.arxiv_url)+'" target="_blank">arXiv</a>':'')+(p.pdf_url?'<a href="'+esc(p.pdf_url)+'" target="_blank">PDF</a>':'')+'</div>'+
'</div>';}
function markRead(id){
const paper=D.find(x=>x.id===id);if(!paper)return;
paper.read=true;
const el=document.getElementById('card-'+id);
if(el&&cf!=='read'){el.classList.add('fade-out');setTimeout(function(){render();},400);}else{render();}
undoStack.push(id);
updateFab();
fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page_id:id,property:'Read',value:true})});
}
function markUnread(id){
const paper=D.find(x=>x.id===id);if(!paper)return;
paper.read=false;
render();
fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page_id:id,property:'Read',value:false})});
}
function updateFab(){
const fab=document.getElementById('undo-fab');
const badge=document.getElementById('undo-badge');
if(undoStack.length>0){fab.classList.add('show');badge.textContent=undoStack.length;}
else{fab.classList.remove('show');}
}
function doUndo(){
if(!undoStack.length)return;
const id=undoStack.pop();
markUnread(id);
updateFab();
}
function togFocus(id,val,btn){
const paper=D.find(x=>x.id===id);
if(paper)paper.focus=val;
btn.classList.toggle('fv',val);
fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({page_id:id,property:'Focus',value:val})});
}
document.getElementById('fl').onclick=function(e){
if(!e.target.classList.contains('fb'))return;
document.querySelectorAll('.fb').forEach(function(b){b.classList.remove('on');});
e.target.classList.add('on');cf=e.target.dataset.f;render();};
load();
</script>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/papers":
            try:
                data = get_papers()
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/toggle":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                notion_req("PATCH", f"pages/{body['page_id']}", {
                    "properties": {body["property"]: {"checkbox": body["value"]}}
                })
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
