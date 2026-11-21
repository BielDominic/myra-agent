# -*- coding: utf-8 -*-
"""MYRA Cognitive Core: routing, persistent memory, traces and scheduled operatives.

Local-first SQLite/FTS5 implementation. Optional Ollama embeddings are used
when an embedding model is configured and available; FTS5 remains the reliable
offline fallback. Scheduled actions are explicit user-created task prompts.
"""
from __future__ import annotations
import json, os, re, sqlite3, threading, time, uuid, urllib.request, contextvars
from contextlib import contextmanager
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["cognitive-core"])

@contextmanager
def _db_session():
    db = _connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
from typing import Any

_lock = threading.RLock()
_worker = None
_stop = threading.Event()
_task_busy = None
_scheduled_mode = contextvars.ContextVar("myra_scheduled_mode", default=False)
SCHEDULED_READ_ONLY_TOOLS = {
    "get_current_time", "get_weather", "read_notes", "list_dir", "read_file",
    "email_list", "email_read", "email_search", "get_current_url",
    "browser_get_tabs", "browser_read_page", "browser_read_active_tab",
    "read_page_structured", "search_google_structured", "web_search_structured",
    "youtube_search", "youtube_channel_latest", "pc_get_active_window",
    "pc_screenshot", "pc_list_controls", "get_system_info", "get_gpu_status",
}

def is_scheduled_execution() -> bool:
    return bool(_scheduled_mode.get())

def is_safe_scheduled_tool(name: str) -> bool:
    return name in SCHEDULED_READ_ONLY_TOOLS

def _db_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MYRA"
    path = Path(os.environ.get("MYRA_COGNITIVE_DB", str(root / "cognitive.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def _connect():
    db = sqlite3.connect(str(_db_path()), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=15000")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS memory(
      id TEXT PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL DEFAULT '',
      title TEXT NOT NULL DEFAULT '', content TEXT NOT NULL, created_at REAL NOT NULL,
      updated_at REAL NOT NULL, UNIQUE(source,source_id,title));
    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
      id UNINDEXED,title,content,source, tokenize='unicode61 remove_diacritics 2');
    CREATE TABLE IF NOT EXISTS traces(
      id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id TEXT NOT NULL, task_id TEXT,
      conversation_id TEXT, agent TEXT, event TEXT NOT NULL, tool TEXT,
      ok INTEGER, latency_ms REAL, detail TEXT, created_at REAL NOT NULL);
    CREATE INDEX IF NOT EXISTS traces_created ON traces(created_at);
    CREATE INDEX IF NOT EXISTS traces_tool ON traces(tool,created_at);
    CREATE TABLE IF NOT EXISTS schedules(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, prompt TEXT NOT NULL,
      interval_seconds INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
      next_run REAL NOT NULL, last_run REAL, last_status TEXT, last_result TEXT,
      created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS schedule_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id TEXT NOT NULL,
      started_at REAL NOT NULL, finished_at REAL, status TEXT, result TEXT);
    """)
    columns = {row[1] for row in db.execute("PRAGMA table_info(memory)").fetchall()}
    if "embedding" not in columns:
        db.execute("ALTER TABLE memory ADD COLUMN embedding TEXT")
    if "embedding_model" not in columns:
        db.execute("ALTER TABLE memory ADD COLUMN embedding_model TEXT")
    db.commit()
    return db

def _embed(text: str):
    model = os.environ.get("MYRA_EMBEDDING_MODEL", "nomic-embed-text").strip()
    if not model:
        return None
    try:
        request = urllib.request.Request("http://127.0.0.1:11434/api/embed",
            data=json.dumps({"model":model,"input":str(text)[:8000],"keep_alive":"10m"}).encode("utf-8"),
            headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request, timeout=12) as response:
            data=json.loads(response.read().decode("utf-8"))
        vector=(data.get("embeddings") or [None])[0]
        if not isinstance(vector,list) or not vector:
            return None
        return [float(x) for x in vector]
    except Exception:
        return None

def _cosine(left, right):
    if not left or not right or len(left)!=len(right): return -1.0
    dot=sum(a*b for a,b in zip(left,right)); ln=sum(a*a for a in left)**0.5; rn=sum(b*b for b in right)**0.5
    return dot/(ln*rn) if ln and rn else -1.0

def classify_agent(text: str, has_image: bool=False) -> dict:
    q = str(text or "").casefold()
    if has_image or any(x in q for x in ("imagem", "foto", "screenshot", "print da tela", "analise visual", "what is in this picture")):
        agent = "vision"
    elif any(x in q for x in ("github", "código", "codigo", "programar", "programação", "programacao", "debug", "python", "javascript", "refator", "compile", "pytest", "bug")):
        agent = "developer"
    elif any(x in q for x in ("pesquise", "pesquisar", "pesquisa", "fontes", "compare", "notícias", "noticias", "research", "look up", "latest", "cite")):
        agent = "research"
    elif any(x in q for x in ("navegue", "abra o site", "acesse", "clique", "preencha", "browser", "website", "navigate", "click on")):
        agent = "browser"
    elif any(x in q for x in ("no meu computador", "abra o aplicativo", "abra o programa", "mova o arquivo", "instale", "desinstale", "controle o pc", "automatize", "execute no windows")):
        agent = "computer"
    else:
        agent = "general"
    return {"agent": agent, "reason": "image" if has_image else "intent_classifier", "confidence": "rule_based"}

def record_trace(event: str, *, task_id=None, conversation_id=None, agent=None,
                 tool=None, ok=None, latency_ms=None, detail=None, trace_id=None):
    payload = json.dumps(detail, ensure_ascii=False, default=str)[:4000] if detail is not None else None
    with _lock, _db_session() as db:
        db.execute("""INSERT INTO traces(trace_id,task_id,conversation_id,agent,event,tool,ok,latency_ms,detail,created_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                   (trace_id or uuid.uuid4().hex, task_id, conversation_id, agent, event, tool,
                    None if ok is None else int(bool(ok)), latency_ms, payload, time.time()))

def index_text(source: str, source_id: str, title: str, content: str) -> dict:
    text = str(content or "").strip()
    if not text: raise ValueError("Conteúdo vazio.")
    if len(text) > 2_000_000: raise ValueError("Documento excede 2 MB de texto.")
    ident = hashlib_id(source + "\0" + source_id + "\0" + title)
    now = time.time()
    embedding = _embed(title + "\n" + text[:6000])
    embedding_json = json.dumps(embedding) if embedding else None
    embedding_model = os.environ.get("MYRA_EMBEDDING_MODEL", "nomic-embed-text") if embedding else None
    with _lock, _db_session() as db:
        db.execute("""INSERT INTO memory(id,source,source_id,title,content,created_at,updated_at,embedding,embedding_model)
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source,source_id,title) DO UPDATE SET
          content=excluded.content,updated_at=excluded.updated_at,embedding=excluded.embedding,embedding_model=excluded.embedding_model""",
          (ident, source[:80], source_id[:300], title[:300], text, now, now, embedding_json, embedding_model))
        row = db.execute("SELECT id FROM memory WHERE source=? AND source_id=? AND title=?",
                         (source[:80], source_id[:300], title[:300])).fetchone()
        ident = row["id"]
        db.execute("DELETE FROM memory_fts WHERE id=?", (ident,))
        db.execute("INSERT INTO memory_fts(id,title,content,source) VALUES(?,?,?,?)",
                   (ident,title[:300],text,source[:80]))
    record_trace("memory_index", detail={"source":source,"id":ident,"chars":len(text)})
    return {"id":ident,"source":source,"title":title,"characters":len(text)}

def hashlib_id(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def search_memory(query: str, limit: int=5) -> list[dict]:
    terms = re.findall(r"[\w-]{2,}", str(query or ""), flags=re.UNICODE)[:16]
    if not terms: return []
    match = " OR ".join('"' + t.replace('"','') + '"' for t in terms)
    query_vector = _embed(query)
    with _db_session() as db:
        if query_vector:
            rows = db.execute("SELECT id,source,source_id,title,content,updated_at,embedding FROM memory WHERE embedding IS NOT NULL").fetchall()
            ranked = []
            for row in rows:
                try: score = _cosine(query_vector, json.loads(row["embedding"]))
                except Exception: continue
                ranked.append((score,row))
            ranked.sort(key=lambda item:item[0], reverse=True)
            semantic = [(score,row) for score,row in ranked[:max(1,min(10,int(limit)))] if score > 0.12]
        else:
            semantic = []
        rows = db.execute("""SELECT m.id,m.source,m.source_id,m.title,m.content,m.updated_at,
          bm25(memory_fts,2.0,1.0,0.3) AS score
          FROM memory_fts JOIN memory m ON m.id=memory_fts.id
          WHERE memory_fts MATCH ? ORDER BY score LIMIT ?""", (match,max(1,min(10,int(limit))))).fetchall()
    results = []
    seen = set()
    for score,row in semantic:
        seen.add(row["id"])
        results.append({"id":row["id"],"source":row["source"],"source_id":row["source_id"],
                        "title":row["title"],"snippet":row["content"][:1200],"updated_at":row["updated_at"],
                        "score":score,"retrieval":"ollama-embedding"})
    for row in rows:
        if row["id"] in seen: continue
        content = row["content"]
        results.append({"id":row["id"],"source":row["source"],"source_id":row["source_id"],
                        "title":row["title"],"snippet":content[:1200],"updated_at":row["updated_at"],
                        "score":row["score"],"retrieval":"fts5"})
    results = results[:max(1,min(10,int(limit)))]
    record_trace("memory_retrieve", detail={"query":query[:300],"results":len(results)})
    return results

def trace_summary(days: int=30) -> dict:
    since=time.time()-max(1,min(365,int(days)))*86400
    with _db_session() as db:
        totals=db.execute("""SELECT COUNT(*) n, SUM(CASE WHEN ok=1 THEN 1 ELSE 0 END) ok,
          AVG(latency_ms) latency FROM traces WHERE created_at>=? AND event='tool_call'""",(since,)).fetchone()
        tools=db.execute("""SELECT tool,COUNT(*) calls,AVG(CASE WHEN ok=1 THEN 1.0 ELSE 0.0 END) success_rate,
          AVG(latency_ms) avg_latency_ms FROM traces WHERE created_at>=? AND event='tool_call'
          AND tool IS NOT NULL GROUP BY tool ORDER BY calls DESC LIMIT 30""",(since,)).fetchall()
        events=db.execute("SELECT event,COUNT(*) count FROM traces WHERE created_at>=? GROUP BY event",(since,)).fetchall()
    n=int(totals["n"] or 0); ok=int(totals["ok"] or 0)
    return {"period_days":days,"tool_calls":n,"successful_calls":ok,
            "success_rate":(ok/n if n else None),"average_latency_ms":totals["latency"],
            "tools":[dict(r) for r in tools],"events":[dict(r) for r in events]}

def create_schedule(name: str, prompt: str, interval_seconds: int) -> dict:
    name=str(name).strip(); prompt=str(prompt).strip(); interval=int(interval_seconds)
    if not name or len(name)>120 or not prompt or len(prompt)>1200: raise ValueError("Nome e tarefa são obrigatórios (limites: 120/1200 caracteres).")
    if interval < 60 or interval > 31536000: raise ValueError("Intervalo deve ser entre 1 minuto e 365 dias.")
    ident=uuid.uuid4().hex[:16]; now=time.time()
    with _db_session() as db:
        db.execute("INSERT INTO schedules(id,name,prompt,interval_seconds,enabled,next_run,created_at) VALUES(?,?,?,?,1,?,?)",
                   (ident,name,prompt,interval,now+interval,now))
    return {"id":ident,"name":name,"prompt":prompt,"interval_seconds":interval,"enabled":True,"next_run":now+interval}

def list_schedules() -> list[dict]:
    with _db_session() as db:
        rows=db.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def set_schedule_enabled(ident: str, enabled: bool) -> bool:
    with _db_session() as db:
        cur=db.execute("UPDATE schedules SET enabled=?,next_run=CASE WHEN ?=1 THEN ? ELSE next_run END WHERE id=?",
                       (int(enabled),int(enabled),time.time()+60,ident))
    return bool(cur.rowcount)

def delete_schedule(ident: str) -> bool:
    with _db_session() as db:
        db.execute("DELETE FROM schedule_runs WHERE schedule_id=?",(ident,))
        cur=db.execute("DELETE FROM schedules WHERE id=?",(ident,))
    return bool(cur.rowcount)

def run_due_schedules(executor, *, now=None, max_parallel=1, is_busy=None) -> int:
    current=time.time() if now is None else float(now)
    eligible=[]
    with _lock, _db_session() as db:
        due=db.execute("SELECT * FROM schedules WHERE enabled=1 AND next_run<=? ORDER BY next_run LIMIT ?",
                       (current,max_parallel)).fetchall()
        for row in due:
            item=dict(row)
            if is_busy and is_busy():
                db.execute("UPDATE schedules SET next_run=? WHERE id=?",(current+60,item["id"]))
                continue
            db.execute("UPDATE schedules SET next_run=? WHERE id=?",(current+int(item["interval_seconds"]),item["id"]))
            cur=db.execute("INSERT INTO schedule_runs(schedule_id,started_at,status) VALUES(?,?,'running')",
                           (item["id"],current))
            eligible.append((item,cur.lastrowid))
    for item,run_id in eligible:
        try:
            token = _scheduled_mode.set(True)
            try:
                result=executor(item["prompt"])
            finally:
                _scheduled_mode.reset(token)
            status="done"; detail=str(result)[:4000]
        except Exception as exc:
            status="error"; detail=f"{type(exc).__name__}: {exc}"[:4000]
        finished=time.time()
        with _lock, _db_session() as db:
            db.execute("UPDATE schedule_runs SET finished_at=?,status=?,result=? WHERE id=?",
                       (finished,status,detail,run_id))
            db.execute("UPDATE schedules SET last_run=?,last_status=?,last_result=? WHERE id=?",
                       (finished,status,detail,item["id"]))
        record_trace("scheduled_run",detail={"schedule_id":item["id"],"status":status})
    return len(eligible)

def start_scheduler(executor, busy_check=None):
    global _worker, _task_busy
    _task_busy = busy_check
    if _worker and _worker.is_alive(): return
    _stop.clear()
    def loop():
        while not _stop.wait(15):
            try: run_due_schedules(executor, is_busy=lambda: bool(_task_busy and _task_busy()))
            except Exception: pass
    _worker=threading.Thread(target=loop,name="myra-scheduler",daemon=True)
    _worker.start()

def stop_scheduler():
    _stop.set()


class MemoryIndexRequest(BaseModel):
    source: str = Field(default="manual", max_length=80)
    source_id: str = Field(default="", max_length=300)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=2_000_000)

class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)

class ScheduleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=1200)
    interval_seconds: int = Field(ge=60, le=31536000)

@router.get("/cognitive/status")
def cognitive_status():
    with _db_session() as db:
        counts = {
            "memory_documents": db.execute("SELECT COUNT(*) FROM memory").fetchone()[0],
            "traces": db.execute("SELECT COUNT(*) FROM traces").fetchone()[0],
            "scheduled_tasks": db.execute("SELECT COUNT(*) FROM schedules").fetchone()[0],
        }
    return {"status":"online","storage":"sqlite-hybrid" if os.environ.get("MYRA_EMBEDDING_MODEL","nomic-embed-text") else "sqlite-fts5","database":str(_db_path()),**counts,
            "embedding_model":os.environ.get("MYRA_EMBEDDING_MODEL","nomic-embed-text") or None,
            "scheduler_running":bool(_worker and _worker.is_alive())}

@router.post("/cognitive/memory/index")
def api_memory_index(data: MemoryIndexRequest):
    try: return index_text(data.source,data.source_id,data.title,data.content)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@router.post("/cognitive/memory/search")
def api_memory_search(data: MemorySearchRequest):
    results=search_memory(data.query,data.limit)
    return {"query":data.query,"results":results,"method":"ollama-embedding+fts5" if any(x.get("retrieval")=="ollama-embedding" for x in results) else "fts5"}

@router.post("/cognitive/memory/index-path")
def api_memory_index_path(payload: dict):
    raw=str(payload.get("path") or "").strip()
    if not raw: raise HTTPException(422,"Informe um caminho.")
    candidate=Path(raw).expanduser().resolve(strict=True)
    roots=[]
    for value in (os.environ.get("MYRA_WORKSPACE",""),os.environ.get("MYRA_REPO_ROOT","")):
        if value:
            try: roots.append(Path(value).expanduser().resolve(strict=True))
            except OSError: pass
    git_root = next((parent for parent in (candidate, *candidate.parents) if (parent / ".git").exists()), None)
    inside_configured = any(candidate == root or root in candidate.parents for root in roots)
    inside_user_git = bool(git_root and (candidate == git_root or git_root in candidate.parents))
    if not (inside_configured or inside_user_git):
        raise HTTPException(403,"Informe o workspace configurado ou uma pasta dentro de um repositório Git.")
    allowed={".txt",".md",".rst",".py",".js",".ts",".tsx",".jsx",".json",".yaml",".yml",".toml",".html",".css",".sql",".log"}
    ignored={".git","node_modules",".venv","venv","__pycache__","dist","build","target",".next"}
    files=[candidate] if candidate.is_file() else [p for p in candidate.rglob("*") if p.is_file() and p.suffix.lower() in allowed and not any(part in ignored for part in p.parts)]
    files=[p for p in files if p.suffix.lower() in allowed][:100]
    indexed=[]; errors=[]
    for path in files:
        try:
            if path.stat().st_size > 2_000_000: continue
            content=path.read_text(encoding="utf-8",errors="replace")
            indexed.append(index_text("project",str(path),path.name,content))
        except Exception as exc: errors.append({"path":str(path),"error":type(exc).__name__})
    return {"indexed":len(indexed),"items":indexed,"errors":errors[:20]}

@router.get("/cognitive/traces/summary")
def api_trace_summary(days: int=30):
    return trace_summary(days)

@router.get("/cognitive/schedules")
def api_list_schedules():
    return {"schedules":list_schedules()}

@router.post("/cognitive/schedules")
def api_create_schedule(data: ScheduleRequest):
    try: return create_schedule(data.name,data.prompt,data.interval_seconds)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@router.post("/cognitive/schedules/{schedule_id}/toggle")
def api_toggle_schedule(schedule_id: str, payload: dict):
    enabled=bool(payload.get("enabled"))
    if not set_schedule_enabled(schedule_id,enabled): raise HTTPException(404,"Agendamento não encontrado.")
    return {"id":schedule_id,"enabled":enabled}

@router.delete("/cognitive/schedules/{schedule_id}")
def api_delete_schedule(schedule_id: str):
    if not delete_schedule(schedule_id): raise HTTPException(404,"Agendamento não encontrado.")
    return {"deleted":True,"id":schedule_id}


def route_agent(text: str, has_image: bool=False) -> dict:
    """Intent router with a conservative trace-driven quality guard."""
    route = classify_agent(text, has_image=has_image)
    base = route["agent"]
    if base in {"general", "vision"}:
        return route
    since = time.time() - 30 * 86400
    with _db_session() as db:
        row = db.execute("""SELECT COUNT(*) calls,
          AVG(CASE WHEN ok=1 THEN 1.0 ELSE 0.0 END) success_rate
          FROM traces WHERE event='tool_call' AND agent=? AND created_at>=?""",
          (base, since)).fetchone()
    calls = int(row["calls"] or 0)
    rate = row["success_rate"]
    route["history"] = {"calls": calls, "success_rate": rate}
    if calls >= 5 and rate is not None and rate < 0.35:
        route["agent"] = "general"
        route["reason"] = "low_historical_success_fallback"
        route["confidence"] = "learned_fallback"
    else:
        route["reason"] = "intent_plus_trace_feedback"
    return route


def list_schedule_runs(schedule_id: str, limit: int=20) -> list[dict]:
    with _db_session() as db:
        rows=db.execute("SELECT * FROM schedule_runs WHERE schedule_id=? ORDER BY started_at DESC LIMIT ?",
                        (schedule_id,max(1,min(100,int(limit))))).fetchall()
    return [dict(row) for row in rows]

@router.get("/cognitive/schedules/{schedule_id}/runs")
def api_schedule_runs(schedule_id: str, limit: int=20):
    return {"schedule_id":schedule_id,"runs":list_schedule_runs(schedule_id,limit)}
