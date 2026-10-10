"""Local, token-protected command bridge between MYRA and its Chrome extension."""
from __future__ import annotations

import hmac
import os
import queue
import threading
import time
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()
_commands: queue.Queue = queue.Queue()
_pending: dict[str, dict] = {}
_pending_lock = threading.Lock()
COMMAND_TIMEOUT_SECONDS = 40
MAX_TEXT_LENGTH = 500


class CommandCompletion(BaseModel):
    command_id: str = Field(min_length=1, max_length=80)
    result: dict


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


def _run_command(action: str, **args) -> dict:
    if action not in {"read_active_tab", "navigate_active_tab", "click_text"}:
        return {"status": "erro", "result": "Acao do navegador nao permitida."}
    if action == "navigate_active_tab":
        raw_url = str(args.get("url", "")).strip()
        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {"status": "erro", "result": "URL invalida: use apenas http:// ou https://."}
        args["url"] = raw_url
    if action == "click_text":
        text = str(args.get("text", "")).strip()
        if not text or len(text) > MAX_TEXT_LENGTH:
            return {"status": "erro", "result": "Informe o texto do botao/link (ate 500 caracteres)."}
        args["text"] = text

    command_id = uuid.uuid4().hex
    completed = threading.Event()
    item = {"id": command_id, "action": action, "args": args, "event": completed, "result": None}
    with _pending_lock:
        _pending[command_id] = item
    _commands.put({"command_id": command_id, "action": action, "args": args})

    if not completed.wait(COMMAND_TIMEOUT_SECONDS):
        with _pending_lock:
            _pending.pop(command_id, None)
        return {
            "status": "erro",
            "result": "Tempo esgotado aguardando a extensão. Abra o Chrome, habilite a extensão MYRA e confira o token.",
        }

    result = item.get("result") or {"ok": False, "error": "A extensão não devolveu resultado."}
    if not result.get("ok"):
        return {"status": "erro", "result": str(result.get("error") or "A ação no Chrome falhou.")}
    payload = result.get("result", result)
    return {"status": "ok", "result": payload, **(payload if isinstance(payload, dict) else {})}


def browser_read_active_tab() -> dict:
    """Lê o título, URL e texto visível da aba ativa do Chrome autenticado."""
    return _run_command("read_active_tab")


def browser_navigate_active_tab(url: str) -> dict:
    """Navega a aba ativa do Chrome para uma URL HTTP/HTTPS."""
    return _run_command("navigate_active_tab", url=url)


def browser_click_text(text: str) -> dict:
    """Clica em um botão/link visível cujo texto corresponda exatamente ao informado."""
    return _run_command("click_text", text=text)


def registrar_ferramentas(registrar_ferramenta) -> None:
    registrar_ferramenta(
        "browser_read_active_tab",
        browser_read_active_tab,
        "Lê título, URL e texto visível da aba ativa do Chrome do usuário, usando a extensão MYRA. Sem argumentos. Requer Chrome aberto e Browser Bridge habilitado."
    )
    registrar_ferramenta(
        "browser_navigate_active_tab",
        browser_navigate_active_tab,
        "Abre uma URL http/https na aba ativa do Chrome do usuário, usando a extensão MYRA. Obrigatório: url='https://...'."
    )
    registrar_ferramenta(
        "browser_click_text",
        browser_click_text,
        "Clica em botão/link cujo texto corresponda exatamente. Obrigatório: text='Continuar'. Use apenas quando a ação estiver claramente autorizada pelo objetivo do usuário."
    )


@router.get("/browser_bridge/next")
def browser_bridge_next(request: Request, token: str, wait: int = 20):
    _require_local_and_token(request, token)
    wait_seconds = max(0, min(int(wait), 25))
    try:
        command = _commands.get(timeout=wait_seconds)
        return {"status": "ok", "command": command}
    except queue.Empty:
        return {"status": "ok", "command": None}


@router.post("/browser_bridge/complete")
def browser_bridge_complete(data: CommandCompletion, request: Request, token: str):
    _require_local_and_token(request, token)
    with _pending_lock:
        item = _pending.get(data.command_id)
        if not item:
            raise HTTPException(status_code=404, detail="Comando expirado ou desconhecido.")
        item["result"] = data.result
        item["event"].set()
        _pending.pop(data.command_id, None)
    return {"status": "ok", "completed": True}
