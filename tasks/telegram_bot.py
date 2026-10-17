"""Telegram remote control for MYRA, disabled unless secrets and chat allowlist exist.

Uses long polling instead of an inbound webhook: no public port or webhook URL is
needed. All computer-control commands are restricted to configured chat IDs.
"""
from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import requests


DEFAULT_AGENT_URL = "http://127.0.0.1:8000"
MAX_MESSAGE_LENGTH = 3900
MAX_TASK_LENGTH = 1200


class TelegramBot:
    def __init__(
        self,
        token: str = "",
        allowed_chat_ids: set[str] | None = None,
        agent_url: str = DEFAULT_AGENT_URL,
        api_base: str = "https://api.telegram.org",
        http: Any = None,
    ):
        self.token = (token or "").strip()
        self.allowed_chat_ids = {str(value).strip() for value in (allowed_chat_ids or set()) if str(value).strip()}
        self.agent_url = agent_url.rstrip("/")
        self.api_base = api_base.rstrip("/")
        self.http = http or requests.Session()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0
        self._task_lock = threading.Lock()
        self._task_running = False
        self._last_error: str | None = None

    @classmethod
    def from_env(cls) -> "TelegramBot":
        allowed = {
            item.strip()
            for item in os.getenv("MYRA_TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
            if item.strip()
        }
        return cls(
            token=os.getenv("MYRA_TELEGRAM_BOT_TOKEN", ""),
            allowed_chat_ids=allowed,
            agent_url=os.getenv("MYRA_API_URL", DEFAULT_AGENT_URL),
            api_base=os.getenv("MYRA_TELEGRAM_API_BASE", "https://api.telegram.org"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.token and self.allowed_chat_ids)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())

    def status(self) -> dict:
        return {
            "status": "ok",
            "configured": self.configured,
            "running": self.running,
            "allowed_chat_count": len(self.allowed_chat_ids),
            "task_command_running": self._task_running,
            "last_error": self._last_error,
            "transport": "long_polling",
        }

    def start(self) -> dict:
        if not self.configured:
            return {
                "status": "erro",
                "result": "Configure MYRA_TELEGRAM_BOT_TOKEN e MYRA_TELEGRAM_ALLOWED_CHAT_IDS antes de iniciar.",
            }
        if self.running:
            return {"status": "ok", "result": "Bot Telegram ja esta em execucao."}
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, name="myra-telegram", daemon=True)
        self._thread.start()
        return {"status": "ok", "result": "Bot Telegram iniciado com lista de chats autorizados."}

    def stop(self) -> dict:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        return {"status": "ok", "result": "Parada solicitada."}

    def _telegram(self, method: str, *, params=None, data=None, files=None, timeout=15) -> dict:
        url = f"{self.api_base}/bot{self.token}/{method}"
        response = self.http.post(url, data=data, files=files, timeout=timeout) if files else (
            self.http.get(url, params=params, timeout=timeout) if params is not None
            else self.http.post(url, json=data or {}, timeout=timeout)
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError("Telegram API recusou a operacao.")
        return payload

    def _send_message(self, chat_id: str | int, text: str) -> bool:
        content = str(text or "Sem resposta.")[:MAX_MESSAGE_LENGTH]
        try:
            self._telegram("sendMessage", data={"chat_id": str(chat_id), "text": content})
            return True
        except Exception as exc:
            self._last_error = f"sendMessage: {type(exc).__name__}"
            return False

    def _agent_request(self, method: str, route: str, payload: dict | None = None, timeout: int = 20) -> dict:
        response = self.http.request(
            method,
            f"{self.agent_url}{route}",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {"status": "ok", "result": result}

    @staticmethod
    def _short_result(data: dict, fallback: str = "Operacao concluida.") -> str:
        value = data.get("result") or data.get("resultado_final") or data.get("erro") or fallback
        return str(value)[:MAX_MESSAGE_LENGTH]

    def handle_update(self, update: dict) -> None:
        message = update.get("message") or update.get("edited_message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not chat_id or chat_id not in self.allowed_chat_ids:
            return
        text = str(message.get("text") or "").strip()
        if not text.startswith("/"):
            return

        match = re.match(r"^/([a-zA-Z_]+)(?:@[A-Za-z0-9_]+)?(?:\s+(.*))?$", text, re.DOTALL)
        if not match:
            self._send_message(chat_id, "Comando invalido. Use /help.")
            return
        command = match.group(1).lower()
        argument = (match.group(2) or "").strip()

        if command in {"start", "help"}:
            self._send_message(
                chat_id,
                "MYRA local — comandos autorizados:\n"
                "/task <objetivo> — iniciar uma tarefa\n"
                "/status — estado atual\n"
                "/cancel — cancelar a tarefa atual\n"
                "/pause — pausar no proximo ponto seguro\n"
                "/resume <task_id> — retomar tarefa persistida\n"
                "/screenshot — enviar captura da tela\n"
                "/see [pergunta] — descrever a tela com o modelo visual",
            )
        elif command == "status":
            try:
                status = self._agent_request("GET", "/task_status")
                lines = [
                    f"Estado: {status.get('state', 'desconhecido')}",
                    f"Objetivo: {status.get('objetivo') or '—'}",
                    f"Passo: {status.get('passo_atual') or '—'}",
                ]
                if status.get("erro"):
                    lines.append(f"Erro: {status['erro']}")
                if status.get("resultado"):
                    lines.append(f"Resultado: {status['resultado']}")
                self._send_message(chat_id, "\n".join(lines))
            except Exception as exc:
                self._send_message(chat_id, f"Falha ao consultar MYRA: {type(exc).__name__}.")
        elif command == "task":
            if not argument:
                self._send_message(chat_id, "Uso: /task descreva o que MYRA deve fazer.")
                return
            if len(argument) > MAX_TASK_LENGTH:
                self._send_message(chat_id, f"Objetivo muito longo; limite de {MAX_TASK_LENGTH} caracteres.")
                return
            try:
                current = self._agent_request("GET", "/task_status")
                if current.get("state") == "running":
                    self._send_message(chat_id, "Ja existe uma tarefa em execucao. Use /status ou /cancel.")
                    return
            except Exception:
                self._send_message(chat_id, "Nao consegui contactar o backend local da MYRA.")
                return
            with self._task_lock:
                if self._task_running:
                    self._send_message(chat_id, "Ja existe um comando /task em andamento.")
                    return
                self._task_running = True
            self._send_message(chat_id, "Tarefa recebida. MYRA vai executa-la; use /status para acompanhar.")
            threading.Thread(
                target=self._run_task,
                args=(chat_id, argument),
                name="myra-telegram-task",
                daemon=True,
            ).start()
        elif command == "cancel":
            self._command_request(chat_id, "POST", "/task_cancel", {}, "Cancelamento solicitado.")
        elif command == "pause":
            self._command_request(chat_id, "POST", "/task_pause", {}, "Pausa solicitada.")
        elif command == "resume":
            if not argument:
                self._send_message(chat_id, "Uso: /resume <task_id>.")
                return
            self._command_request(
                chat_id, "POST", "/task_resume",
                {"task_id": argument, "max_passos": 30}, "Retomada solicitada.",
            )
        elif command == "screenshot":
            self._send_screenshot(chat_id)
        elif command == "see":
            question = argument or "Descreva em portugues o que aparece na tela e o estado atual."
            try:
                result = self._agent_request("POST", "/see", {"pergunta": question}, timeout=150)
                self._send_message(chat_id, self._short_result(result, "Analise visual concluida."))
            except Exception as exc:
                self._send_message(chat_id, f"Falha na analise visual: {type(exc).__name__}.")
        else:
            self._send_message(chat_id, "Comando desconhecido. Use /help.")

    def _command_request(self, chat_id: str, method: str, route: str, payload: dict, fallback: str) -> None:
        try:
            result = self._agent_request(method, route, payload, timeout=20)
            self._send_message(chat_id, self._short_result(result, fallback))
        except Exception as exc:
            self._send_message(chat_id, f"Falha ao contactar MYRA: {type(exc).__name__}.")

    def _run_task(self, chat_id: str, objective: str) -> None:
        try:
            result = self._agent_request(
                "POST", "/task_simple",
                {"objetivo": objective, "max_passos": 30},
                timeout=1800,
            )
            state = result.get("status", "concluida")
            text = self._short_result(result, "Tarefa finalizada.")
            self._send_message(chat_id, f"Tarefa {state}.\n{text}")
        except Exception as exc:
            self._send_message(chat_id, f"A tarefa terminou com erro de comunicacao: {type(exc).__name__}.")
        finally:
            with self._task_lock:
                self._task_running = False

    def _send_screenshot(self, chat_id: str) -> None:
        try:
            result = self._agent_request("POST", "/pc_screenshot", {"salvar": True}, timeout=30)
            path_text = result.get("path") or result.get("arquivo") or result.get("screenshot")
            if not path_text:
                self._send_message(chat_id, self._short_result(result, "Nao foi possivel obter o caminho da captura."))
                return
            path = Path(path_text)
            if not path.is_file():
                self._send_message(chat_id, f"Captura criada, mas o arquivo nao foi encontrado: {path.name}")
                return
            with path.open("rb") as image_file:
                self._telegram(
                    "sendPhoto",
                    data={"chat_id": str(chat_id), "caption": f"Captura MYRA: {path.name}"},
                    files={"photo": (path.name, image_file, "image/png")},
                    timeout=60,
                )
        except Exception as exc:
            self._send_message(chat_id, f"Falha ao enviar captura: {type(exc).__name__}.")

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                payload = self._telegram(
                    "getUpdates",
                    params={"offset": self._offset, "timeout": 25, "allowed_updates": '["message"]'},
                    timeout=35,
                )
                for update in payload.get("result", []):
                    try:
                        self.handle_update(update)
                    except Exception as exc:
                        self._last_error = f"update: {type(exc).__name__}"
                    self._offset = max(self._offset, int(update.get("update_id", 0)) + 1)
            except Exception as exc:
                self._last_error = f"polling: {type(exc).__name__}"
                self._stop_event.wait(3)


def criar_bot_do_ambiente() -> TelegramBot:
    return TelegramBot.from_env()
