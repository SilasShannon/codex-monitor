from __future__ import annotations

import ipaddress
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ..analytics import cost_summary, session_costs, usage_breakdown, usage_timeseries
from ..config import Config
from ..database import Database
from ..indexer import Indexer
from ..queries import overview, projects, session_detail, sessions
from ..sources.otel import OtelReceiver

INDEX_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Codex Monitor</title><style>
:root{color-scheme:dark;--bg:#0a0d12;--card:#141923;--line:#283142;--text:#e8edf5;--muted:#91a0b5;--accent:#7ce7c4}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#172235,var(--bg) 35%);color:var(--text);font:14px system-ui,sans-serif}
header{position:sticky;top:0;background:#0a0d12e8;border-bottom:1px solid var(--line);padding:18px 4vw;display:flex;gap:28px;align-items:center}h1{font-size:19px;margin:0;color:var(--accent)}nav button{border:0;background:none;color:var(--muted);padding:8px;cursor:pointer}nav button:hover{color:white}
main{max-width:1300px;margin:32px auto;padding:0 24px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}.card,.panel{background:linear-gradient(145deg,#171d28,#111620);border:1px solid var(--line);border-radius:14px;padding:18px}.value{font-size:28px;font-weight:700;margin-top:7px}.muted{color:var(--muted)}.panel{margin-top:20px;overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}a{color:var(--accent)}input{background:#0d1118;color:white;border:1px solid var(--line);padding:10px;border-radius:8px;width:min(420px,100%)}
</style></head><body><header><h1>CODEX MONITOR</h1><nav><button onclick="showOverview()">Overview</button><button onclick="showProjects()">Projects</button><button onclick="showSessions()">Sessions</button></nav></header><main id="app"></main>
<script>
const app=document.querySelector('#app'); const esc=s=>String(s??'UNKNOWN / NOT EXPOSED').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>n==null?'UNKNOWN / NOT EXPOSED':Number(n).toLocaleString(); async function api(p){let r=await fetch(p);if(!r.ok)throw Error(r.status);return r.json()}
const usd=n=>n==null?'UNAVAILABLE':'$'+Number(n).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:4});
async function showOverview(){let [o,c,s]=await Promise.all([api('/api/overview'),api('/api/cost/summary'),api('/api/sessions?limit=8')]);app.innerHTML=`<h2>Overview</h2><div class=cards>${[['Active sessions',o.active_sessions],['Tokens',o.total_tokens],['API equivalent today',usd(c.today)],['API equivalent · 7 days',usd(c['7_days'])],['API equivalent · 30 days',usd(c['30_days'])],['Cache rate',o.cache_rate==null?'UNAVAILABLE':Math.round(o.cache_rate*100)+'%'],['Estimated cache savings',usd(c.cache_savings)]].map(x=>`<div class=card><span class=muted>${x[0]}</span><div class=value>${x[1]}</div></div>`).join('')}</div><p class=muted>All monetary values are estimated API-equivalent cost, not actual subscription charges. ${fmt(c.unavailable_sessions)} sessions cannot be priced with current evidence.</p>${sessionTable(s)}`}
function sessionTable(rows){return `<div class=panel><h3>Sessions</h3><table><thead><tr><th>Project</th><th>Session</th><th>Model</th><th>Last activity</th><th>Tokens</th></tr></thead><tbody>${rows.map(s=>`<tr><td>${esc(s.project_name)}</td><td><a href="#" onclick="showSession('${encodeURIComponent(s.session_id)}')">${esc(s.session_id.slice(0,16))}</a></td><td>${esc(s.model)}</td><td>${esc(s.last_activity)}</td><td>${fmt(s.total_tokens)}</td></tr>`).join('')}</tbody></table></div>`}
async function showProjects(){let p=await api('/api/projects');app.innerHTML=`<h2>Projects</h2><div class=cards>${p.map(x=>`<div class=card><h3>${esc(x.name)}</h3><div class=muted>${esc(x.git_root||x.working_directory)}</div><p>${fmt(x.session_count)} sessions · ${fmt(x.total_tokens)} tokens</p></div>`).join('')}</div>`}
async function showSessions(){app.innerHTML='<h2>Sessions</h2><input id=q placeholder="Search project, session, path, title"><div id=results></div>';let go=async()=>document.querySelector('#results').innerHTML=sessionTable(await api('/api/sessions?search='+encodeURIComponent(document.querySelector('#q').value)));document.querySelector('#q').oninput=go;go()}
async function showSession(id){let s=await api('/api/sessions/'+id);app.innerHTML=`<h2>${esc(s.title||s.session_id)}</h2><div class=cards><div class=card><span class=muted>Project</span><div>${esc(s.project_name)}</div></div><div class=card><span class=muted>Model</span><div>${esc(s.model)}</div></div><div class=card><span class=muted>Tokens</span><div>${fmt(s.total_tokens)}</div></div></div><div class=panel><h3>Activity timeline</h3><table>${s.events.map(e=>`<tr><td>${esc(e.timestamp)}</td><td>${esc(e.category)} / ${esc(e.subtype)}</td></tr>`).join('')}</table></div>`}
showOverview();setInterval(()=>{if(!location.hash)showOverview()},5000);
</script></body></html>'''


class DashboardHandler(BaseHTTPRequestHandler):
    db: Database

    def _json(self, value: object, status: int = 200) -> None:
        payload = json.dumps(value, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]")
        try:
            trusted = host == "localhost" or ipaddress.ip_address(host) is not None
        except ValueError:
            trusted = False
        if not trusted:
            return self._json({"error": "untrusted Host header"}, HTTPStatus.FORBIDDEN)
        origin = self.headers.get("Origin")
        if origin and origin.rstrip("/") != f"http://{self.headers.get('Host')}".rstrip("/"):
            return self._json({"error": "cross-origin request refused"}, HTTPStatus.FORBIDDEN)
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path.startswith("/assets/"):
            static_root = Path(__file__).with_name("static").resolve()
            relative = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
            target = (static_root / relative).resolve()
            if static_root not in target.parents or not target.is_file():
                return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            body = target.read_bytes()
            self.send_response(200)
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self'")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/overview":
            return self._json(overview(self.db))
        if parsed.path == "/api/cost/summary":
            return self._json(cost_summary(self.db))
        if parsed.path == "/api/cost/sessions":
            return self._json(session_costs(self.db))
        if parsed.path == "/api/analytics/timeseries":
            query = parse_qs(parsed.query)
            try:
                days = min(max(int(query.get("days", [30])[0]), 1), 366)
            except ValueError:
                return self._json({"error": "invalid days"}, HTTPStatus.BAD_REQUEST)
            return self._json(usage_timeseries(self.db, days))
        if parsed.path == "/api/analytics/breakdown":
            query = parse_qs(parsed.query)
            dimension = query.get("dimension", ["project"])[0]
            sort_by = query.get("sort", ["tokens"])[0]
            try:
                return self._json(usage_breakdown(self.db, dimension, sort_by=sort_by))
            except ValueError as exc:
                return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        if parsed.path == "/api/projects":
            return self._json(projects(self.db))
        if parsed.path == "/api/sessions":
            query = parse_qs(parsed.query)
            try:
                limit = min(max(int(query.get("limit", [100])[0]), 1), 1000)
            except ValueError:
                return self._json({"error": "invalid limit"}, HTTPStatus.BAD_REQUEST)
            return self._json(sessions(self.db, limit, query.get("search", [None])[0]))
        prefix = "/api/sessions/"
        if parsed.path.startswith(prefix):
            session_id = unquote(parsed.path[len(prefix):])
            if not session_id or len(session_id) > 500 or "/" in session_id:
                return self._json({"error": "invalid session id"}, HTTPStatus.BAD_REQUEST)
            detail = session_detail(self.db, session_id)
            return self._json(detail or {"error": "not found"}, 200 if detail else 404)
        self._json({"error": "not found"}, 404)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(config: Config, db: Database, host: str, port: int, open_browser: bool = False) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: Codex session history is sensitive; this server has no authentication.")
    DashboardHandler.db = db
    stop = threading.Event()

    def refresh() -> None:
        refresh_db = Database(db.path)
        indexer = Indexer(config, refresh_db)
        try:
            while not stop.wait(config.scan_interval):
                indexer.scan()
        finally:
            refresh_db.close()

    Indexer(config, db).scan()
    receiver = None
    if config.otel_enabled:
        receiver = OtelReceiver(config.database_path, config.otel_host, config.otel_port)
        receiver.start()
    threading.Thread(target=refresh, daemon=True).start()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}"
    print(f"Codex Monitor web dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if receiver:
            receiver.close()
        server.server_close()
