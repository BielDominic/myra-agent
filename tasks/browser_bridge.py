"""Local, token-protected command bridge between MYRA and its Chrome extension.

Commands and results are stored in SQLite so the planner/tool caller and the
FastAPI polling endpoints can communicate even if they run in separate Python
processes. Set MYRA_BROWSER_BRIDGE_DB to override the database location.
"""
from __future__ import annotations

import hmac
from contextlib import closing
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()
COMMAND_TIMEOUT_SECONDS = max(
    10, int(os.environ.get("MYRA_BROWSER_BRIDGE_TIMEOUT_SECONDS", "90"))
)
MAX_TEXT_LENGTH = 500
MAX_URL_CONTAINS_LENGTH = 300
POLL_INTERVAL_SECONDS = 0.1
_db_initialized = False
_db_init_lock = threading.Lock()


class CommandCompletion(BaseModel):
    command_id: str = Field(min_length=1, max_length=80)
    result: dict


def _database_path() -> Path:
    configured = os.environ.get("MYRA_BROWSER_BRIDGE_DB", "").strip()
    if configured:
        path = Path(configured).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_app_data) / "MYRA" if local_app_data else Path.home() / ".myra"
        path = base / "browser_bridge.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect_db() -> sqlite3.Connection:
    global _db_initialized
    conn = sqlite3.connect(str(_database_path()), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        if not _db_initialized:
            with _db_init_lock:
                if not _db_initialized:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS browser_bridge_commands (
                            command_id TEXT PRIMARY KEY,
                            action TEXT NOT NULL,
                            args_json TEXT NOT NULL,
                            status TEXT NOT NULL CHECK(status IN ('queued', 'delivered', 'completed')),
                            result_json TEXT,
                            created_at REAL NOT NULL,
                            updated_at REAL NOT NULL
                        )
                        """
                    )
                    conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_browser_bridge_queue "
                        "ON browser_bridge_commands(status, created_at)"
                    )
                    conn.commit()
                    _db_initialized = True
        return conn
    except Exception:
        conn.close()
        raise


def _require_local_and_token(request: Request, token: str | None = None) -> None:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Bridge aceita apenas conexoes locais.")
    expected = os.environ.get("MYRA_BROWSER_BRIDGE_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Configure MYRA_BROWSER_BRIDGE_TOKEN e reinicie o backend.")
    supplied = token or ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Token do Browser Bridge invalido.")


def _enqueue_command(command_id: str, action: str, args: dict) -> None:
    now = time.time()
    with closing(_connect_db()) as conn:
        conn.execute(
            """
            INSERT INTO browser_bridge_commands
                (command_id, action, args_json, status, created_at, updated_at)
            VALUES (?, ?, ?, 'queued', ?, ?)
            """,
            (command_id, action, json.dumps(args, ensure_ascii=False), now, now),
        )
        conn.commit()
    print(
        f"[Bridge] ENQUEUE pid={os.getpid()} id={command_id} "
        f"action={action} db={_database_path()}",
        flush=True,
    )


def _take_next_command() -> dict | None:
    # BEGIN IMMEDIATE makes selection + claim atomic across concurrent pollers.
    with closing(_connect_db()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT command_id, action, args_json
            FROM browser_bridge_commands
            WHERE status = 'queued'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            conn.commit()
            return None
        now = time.time()
        conn.execute(
            """
            UPDATE browser_bridge_commands
            SET status = 'delivered', updated_at = ?
            WHERE command_id = ? AND status = 'queued'
            """,
            (now, row["command_id"]),
        )
        conn.commit()
    command = {
        "command_id": row["command_id"],
        "action": row["action"],
        "args": json.loads(row["args_json"]),
    }
    print(
        f"[Bridge] DEQUEUE pid={os.getpid()} id={command['command_id']} "
        f"action={command['action']}",
        flush=True,
    )
    return command


def _read_command(command_id: str) -> dict | None:
    with closing(_connect_db()) as conn:
        row = conn.execute(
            "SELECT status, result_json FROM browser_bridge_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "status": row["status"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }


def _delete_command(command_id: str) -> None:
    with closing(_connect_db()) as conn:
        conn.execute(
            "DELETE FROM browser_bridge_commands WHERE command_id = ?",
            (command_id,),
        )
        conn.commit()


def _run_command(action: str, *, timeout_seconds: int | None = None, **args) -> dict:
    if action not in {"read_active_tab", "read_page_url", "navigate_active_tab", "click_text", "get_tabs", "type_text", "new_tab", "close_tab", "scroll", "search_google"}:
        return {"status": "erro", "result": "Acao do navegador nao permitida."}
    if action == "read_page_url":
        raw_url = str(args.get("url", "")).strip()
        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {"status": "erro", "result": "URL invalida: use apenas http:// ou https://."}
        args["url"] = raw_url
    if action in {"navigate_active_tab", "new_tab"}:
        raw_url = str(args.get("url", "")).strip()
        parsed = urlparse(raw_url)
        if len(raw_url) > 2000 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {"status": "erro", "result": "URL invalida: use uma URL HTTP/HTTPS completa com até 2000 caracteres."}
        args["url"] = raw_url
    if action == "read_active_tab":
        url_contains = str(args.get("url_contains") or "").strip()
        if len(url_contains) > MAX_URL_CONTAINS_LENGTH:
            return {"status": "erro", "result": "url_contains deve ter no máximo 300 caracteres."}
        if url_contains:
            args["url_contains"] = url_contains
        else:
            args.pop("url_contains", None)
    if action == "search_google":
        term = str(args.get("term", "")).strip()
        if not term or len(term) > 200:
            return {"status": "erro", "result": "termo deve conter de 1 a 200 caracteres."}
        args["term"] = term
    if action == "scroll":
        direction = str(args.get("direction", "down")).strip().lower()
        amount = args.get("amount", 500)
        if direction not in {"up", "down", "top", "bottom"}:
            return {"status": "erro", "result": 'direcao deve ser "up", "down", "top" ou "bottom".'}
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {"status": "erro", "result": "quantidade deve ser numérica."}
        if isinstance(args.get("amount", 500), bool) or amount < 0 or amount > 100000:
            return {"status": "erro", "result": "quantidade deve estar entre 0 e 100000 pixels."}
        args["direction"] = direction
        args["amount"] = amount
    if action == "close_tab":
        tab_id = args.get("tab_id")
        if tab_id is not None and tab_id != "":
            try:
                parsed_tab_id = int(tab_id)
            except (TypeError, ValueError):
                return {"status": "erro", "result": "tab_id deve ser um ID numerico retornado por browser_get_tabs."}
            if isinstance(tab_id, bool) or parsed_tab_id <= 0 or str(parsed_tab_id) != str(tab_id).strip():
                return {"status": "erro", "result": "tab_id deve ser um inteiro positivo retornado por browser_get_tabs."}
            args["tab_id"] = parsed_tab_id
        else:
            args.pop("tab_id", None)
    if action == "type_text":
        campo = str(args.get("campo", "")).strip()
        texto = str(args.get("texto", ""))
        if not campo or len(campo) > 500:
            return {"status": "erro", "result": "Informe campo (seletor CSS ou label), com até 500 caracteres."}
        if len(texto) > 5000:
            return {"status": "erro", "result": "texto deve ter no máximo 5000 caracteres."}
        args["campo"] = campo
        args["texto"] = texto
    if action == "click_text":
        text = str(args.get("text", "")).strip()
        if not text or len(text) > MAX_TEXT_LENGTH:
            return {"status": "erro", "result": "Informe o texto do botao/link (ate 500 caracteres)."}
        args["text"] = text

    command_id = uuid.uuid4().hex
    try:
        _enqueue_command(command_id, action, args)
    except Exception as exc:
        print(f"[Bridge] ENQUEUE_ERROR pid={os.getpid()} error={exc!r}", flush=True)
        return {"status": "erro", "result": f"Falha ao enfileirar comando no banco local: {exc}"}

    effective_timeout = COMMAND_TIMEOUT_SECONDS if timeout_seconds is None else max(1, min(int(timeout_seconds), COMMAND_TIMEOUT_SECONDS))
    deadline = time.monotonic() + effective_timeout
    while time.monotonic() < deadline:
        try:
            state = _read_command(command_id)
        except Exception as exc:
            print(f"[Bridge] READ_ERROR id={command_id} error={exc!r}", flush=True)
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if state is None:
            return {
                "status": "erro",
                "result": "O comando desapareceu da fila persistente antes de ser concluído.",
            }
        if state["status"] == "completed":
            result = state["result"] or {
                "ok": False,
                "error": "A extensão não devolveu resultado.",
            }
            _delete_command(command_id)
            if not result.get("ok"):
                return {
                    "status": "erro",
                    "result": str(result.get("error") or "A ação no Chrome falhou."),
                }
            payload = result.get("result", result)
            return {
                "status": "ok",
                "result": payload,
                **(payload if isinstance(payload, dict) else {}),
            }
        time.sleep(POLL_INTERVAL_SECONDS)

    _delete_command(command_id)
    return {
        "status": "erro",
        "result": (
            "Tempo esgotado aguardando a extensão. Confirme que o Chrome está aberto, "
            "a extensão MYRA está habilitada e conectada, e que o token corresponde ao backend."
        ),
    }


def browser_get_tabs() -> dict:
    """Lista abas HTTP/HTTPS abertas no Chrome, excluindo interfaces locais do MYRA."""
    return _run_command("get_tabs")


def browser_read_active_tab(url_contains: str = "") -> dict:
    """Lê título, URL e texto visível de uma aba do Chrome; opcionalmente seleciona por trecho da URL."""
    return _run_command("read_active_tab", url_contains=url_contains)


def browser_read_page(url: str) -> dict:
    """Abre uma URL HTTP/HTTPS numa aba temporaria da extensao, le o conteudo e fecha a aba."""
    return _run_command("read_page_url", url=url)


def _browser_read_active_tab_for_route() -> dict:
    """Tentativa curta para a rota legada poder cair no Playwright se a extensao nao responder."""
    return _run_command("read_active_tab", timeout_seconds=12)


def browser_navigate_active_tab(url: str) -> dict:
    """Navega a aba ativa do Chrome para uma URL HTTP/HTTPS."""
    return _run_command("navigate_active_tab", url=url)


def browser_new_tab(url: str) -> dict:
    """Abre uma URL HTTP/HTTPS completa em uma nova aba ativa do Chrome."""
    return _run_command("new_tab", url=url)


def browser_search_google(termo: str) -> dict:
    """Pesquisa um termo no Google em aba temporária e retorna conteúdo estruturado."""
    return _run_command("search_google", term=termo)


def browser_scroll(direcao: str = "down", quantidade: int = 500) -> dict:
    """Rola a aba web alvo: up/down em pixels ou top/bottom."""
    return _run_command("scroll", direction=direcao, amount=quantidade)


def browser_close_tab(tab_id: int | None = None) -> dict:
    """Fecha uma aba HTTP/HTTPS do Chrome, selecionada pelo ID ou pela aba web alvo."""
    return _run_command("close_tab", **({"tab_id": tab_id} if tab_id is not None else {}))


def browser_type_text(campo: str, texto: str) -> dict:
    """Substitui o conteúdo de um campo de formulário identificado por seletor CSS ou label exato."""
    return _run_command("type_text", campo=campo, texto=texto)


def browser_click_text(text: str) -> dict:
    """Clica em um botão/link visível cujo texto corresponda exatamente ao informado."""
    return _run_command("click_text", text=text)


def registrar_ferramentas(registrar_ferramenta) -> None:
    registrar_ferramenta(
        "browser_get_tabs",
        browser_get_tabs,
        "Lista até 50 abas HTTP/HTTPS abertas no Chrome, da mais recentemente acessada para a mais antiga. Exclui páginas internas, extensões e interfaces locais do Open WebUI. Retorna id, título, URL, estado ativo e janela."
    )
    registrar_ferramenta(
        "browser_read_active_tab",
        browser_read_active_tab,
        "Lê título, URL e texto visível de uma aba do Chrome via extensão MYRA. Opcional: url_contains='github.com' seleciona uma aba cuja URL contenha esse trecho (case-insensitive), útil quando há várias abas. Sem url_contains, usa a aba ativa ou a aba web mais recente se o Open WebUI estiver ativo. Requer Chrome aberto e Browser Bridge habilitado."
    )
    registrar_ferramenta(
        "browser_read_page",
        browser_read_page,
        "Abre uma URL HTTP/HTTPS em uma aba temporaria do Chrome, extrai titulo, URL, texto e links, e fecha a aba temporaria. Obrigatorio: url='https://example.com'. Requer permissao da extensao para o dominio."
    )
    registrar_ferramenta(
        "browser_navigate_active_tab",
        browser_navigate_active_tab,
        "Abre uma URL http/https na aba ativa do Chrome do usuário, usando a extensão MYRA. Obrigatório: url='https://...'."
    )
    registrar_ferramenta(
        "browser_new_tab",
        browser_new_tab,
        "Abre uma URL HTTP/HTTPS completa em uma nova aba ativa do Chrome sem substituir a aba atual. Obrigatório: url='https://example.com'. Retorna tabId, URL, título e estado de carregamento."
    )
    registrar_ferramenta(
        "browser_close_tab",
        browser_close_tab,
        "Fecha uma aba HTTP/HTTPS do Chrome. Opcional: tab_id, usando o ID retornado por browser_get_tabs; sem ID, fecha a aba web alvo. Não fecha páginas internas do Chrome nem a interface do MYRA."
    )
    registrar_ferramenta(
        "browser_type_text",
        browser_type_text,
        "Digita texto em um campo identificado por seletor CSS (ex.: #search, input[name=q], [placeholder=Pesquisar]) ou pelo texto exato de um label acessível. Obrigatórios: campo e texto. Falha se não encontrar ou se houver mais de uma correspondência; limpa o valor anterior e dispara eventos input/change."
    )
    registrar_ferramenta(
        "browser_click_text",
        browser_click_text,
        "Clica em botão/link cujo texto corresponda exatamente. Obrigatório: text='Continuar'. Use apenas quando a ação estiver claramente autorizada pelo objetivo do usuário."
    )


@router.get("/browser_bridge/next")
def browser_bridge_next(
    request: Request,
    token: str = Header(default="", alias="X-MYRA-BRIDGE-TOKEN"),
    wait: int = 20,
):
    _require_local_and_token(request, token)
    wait_seconds = max(0, min(int(wait), 25))
    deadline = time.monotonic() + wait_seconds

    while True:
        command = _take_next_command()
        if command is not None:
            return {"status": "ok", "command": command}
        if time.monotonic() >= deadline:
            return {"status": "ok", "command": None}
        time.sleep(min(POLL_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))


@router.post("/browser_bridge/complete")
def browser_bridge_complete(
    data: CommandCompletion,
    request: Request,
    token: str = Header(default="", alias="X-MYRA-BRIDGE-TOKEN"),
):
    _require_local_and_token(request, token)
    with closing(_connect_db()) as conn:
        row = conn.execute(
            "SELECT status FROM browser_bridge_commands WHERE command_id = ?",
            (data.command_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Comando expirado ou desconhecido.")
        if row["status"] != "completed":
            conn.execute(
                """
                UPDATE browser_bridge_commands
                SET status = 'completed', result_json = ?, updated_at = ?
                WHERE command_id = ?
                """,
                (json.dumps(data.result, ensure_ascii=False), time.time(), data.command_id),
            )
        conn.commit()
    print(
        f"[Bridge] COMPLETE pid={os.getpid()} id={data.command_id}",
        flush=True,
    )
    return {"status": "ok", "completed": True}
