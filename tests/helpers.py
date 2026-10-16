# -*- coding: utf-8 -*-
"""Infraestrutura compartilhada dos testes severos do MYRA.

Regras de ouro (obrigatorias para qualquer teste novo):

1. **Nunca tocar servicos reais.** Use ``sem_rede()`` para garantir que nenhuma
   ligacao TCP e feita (Ollama, backend 8000, visao 8081, Gmail, YouTube).
2. **Nunca escrever fora de diretorios temporarios.** Use ``AmbienteIsolado`` e
   ``workspace_temporario`` para redirecionar os bancos e o WORKSPACE_DIR.
3. **Nunca executar acoes destrutivas reais** (apagar ficheiros do utilizador,
   enviar email, clicar no PC, abrir abas no browser). Simule com mocks.

Este modulo e apenas de apoio: nao contem testes.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

RAIZ_REPO = Path(__file__).resolve().parent.parent


# ============================================================
# Ambiente isolado (variaveis de ambiente + diretorios temporarios)
# ============================================================

class AmbienteIsolado:
    """Redireciona todos os bancos/estado do MYRA para um diretorio temporario.

    Usar como context manager:

        with AmbienteIsolado() as tmp:
            ...
    """

    VARIAVEIS = (
        "MYRA_TASK_DB",
        "MYRA_BROWSER_BRIDGE_DB",
        "MYRA_TEST_MODE",
    )

    def __init__(self) -> None:
        self.tmp: Path | None = None
        self._antigos: dict[str, str | None] = {}

    def __enter__(self) -> Path:
        self.tmp = Path(tempfile.mkdtemp(prefix="myra_test_"))
        valores = {
            "MYRA_TASK_DB": str(self.tmp / "tasks.sqlite3"),
            "MYRA_BROWSER_BRIDGE_DB": str(self.tmp / "browser_bridge.sqlite3"),
            "MYRA_TEST_MODE": "1",
        }
        for var in self.VARIAVEIS:
            self._antigos[var] = os.environ.get(var)
            if var in valores:
                os.environ[var] = valores[var]
        (self.tmp / "workspace").mkdir(parents=True, exist_ok=True)
        (self.tmp / "workspace" / "code").mkdir(parents=True, exist_ok=True)
        (self.tmp / "workspace" / "youtube").mkdir(parents=True, exist_ok=True)
        return self.tmp

    def __exit__(self, *exc) -> bool:
        for var, valor in self._antigos.items():
            if valor is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = valor
        if self.tmp is not None:
            shutil.rmtree(self.tmp, ignore_errors=True)
        return False


@contextmanager
def workspace_temporario(agent_module):
    """Aponta o WORKSPACE_DIR do agent.py (e derivados) para um diretorio temporario.

    O ``WORKSPACE_DIR`` e uma constante de modulo, por isso as rotas de ficheiros
    escreveriam no workspace real sem este patch.
    """
    tmp = Path(tempfile.mkdtemp(prefix="myra_ws_"))
    (tmp / "code").mkdir(parents=True, exist_ok=True)
    (tmp / "youtube").mkdir(parents=True, exist_ok=True)
    patches = [
        mock.patch.object(agent_module, "WORKSPACE_DIR", str(tmp)),
        mock.patch.object(agent_module, "CODE_WORKSPACE", str(tmp / "code")),
        mock.patch.object(agent_module, "YOUTUBE_WORKSPACE", str(tmp / "youtube")),
    ]
    for p in patches:
        p.start()
    try:
        yield tmp
    finally:
        for p in patches:
            p.stop()
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================
# Bloqueio de rede real
# ============================================================

# Portas dos servicos reais que NUNCA podem ser contactados nos testes.
# O loopback noutras portas e permitido porque o asyncio do Windows cria o
# self-pipe com socket.socketpair() (que faz connect a 127.0.0.1:<porta alta>):
# bloquear todo o loopback partia o TestClient.
PORTAS_BLOQUEADAS = frozenset({
    80, 443,                       # HTTP/HTTPS publicos
    25, 143, 465, 587, 993,        # email (SMTP/IMAP)
    3000, 8080, 8082,              # Open WebUI / proxy local
    8000,                          # backend MYRA (agent.py)
    8081,                          # servico de visao (llm-eyes)
    11434,                         # Ollama
    19387,                         # interface DSH
})


@contextmanager
def sem_rede(permitir_loopback: bool = True):
    """Impede ligacoes de rede reais durante o bloco.

    Bloqueia:
      * qualquer destino que nao seja loopback (Internet, LAN, Gmail...);
      * loopback nas portas de servicos reais (Ollama 11434, backend 8000,
        visao 8081, Open WebUI 8080/8082/3000, email) — ver PORTAS_BLOQUEADAS.

    Permite loopback em portas efemeras, necessario para o self-pipe do asyncio
    no Windows (socket.socketpair), usado pelo TestClient.
    """
    import socket as _socket

    real_connect = _socket.socket.connect
    real_create_connection = _socket.create_connection

    def _loopback_permitido(host, porta) -> bool:
        if not permitir_loopback:
            return False
        if str(host) not in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
            return False
        try:
            return int(porta) not in PORTAS_BLOQUEADAS
        except (TypeError, ValueError):
            return False

    def _connect_bloqueado(self, endereco, *args, **kwargs):
        host, porta = (endereco[0], endereco[1]) if isinstance(endereco, tuple) and len(endereco) >= 2 else (None, None)
        if _loopback_permitido(host, porta):
            return real_connect(self, endereco, *args, **kwargs)
        raise OSError(f"rede bloqueada nos testes do MYRA ({host}:{porta}); use mocks")

    def _create_connection_bloqueado(endereco, *args, **kwargs):
        host, porta = (endereco[0], endereco[1]) if isinstance(endereco, tuple) and len(endereco) >= 2 else (None, None)
        if _loopback_permitido(host, porta):
            return real_create_connection(endereco, *args, **kwargs)
        raise OSError(f"rede bloqueada nos testes do MYRA ({host}:{porta}); use mocks")

    with mock.patch.object(_socket.socket, "connect", _connect_bloqueado), \
         mock.patch.object(_socket, "create_connection", _create_connection_bloqueado):
        yield


# ============================================================
# HTTP falso (para tasks/system_tools.py, structured_tools, etc.)
# ============================================================

class RespostaHTTPFalsa:
    """Resposta minima compativel com ``with urlopen(...) as r``."""

    def __init__(self, corpo=b"{}", status: int = 200) -> None:
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self._corpo = corpo
        self.status = status

    def read(self) -> bytes:
        return self._corpo

    def __enter__(self) -> "RespostaHTTPFalsa":
        return self

    def __exit__(self, *exc) -> bool:
        return False


class HTTPFalso:
    """Substitui ``urllib.request.urlopen`` e registra os pedidos.

    Exemplo:

        with HTTPFalso() as http:
            resultado = system_tools.write_file("a.txt", "x")
        http.ultimo["url"]            # rota chamada
        http.ultimo["payload"]        # corpo JSON enviado
    """

    def __init__(self, resposta=None, erro: Exception | None = None) -> None:
        self.resposta = resposta if resposta is not None else RespostaHTTPFalsa({"status": "ok"})
        self.erro = erro
        self.pedidos: list[dict] = []
        self._patch = None

    # -- API publica -------------------------------------------------
    @property
    def ultimo(self) -> dict:
        if not self.pedidos:
            raise AssertionError("nenhum pedido HTTP foi feito")
        return self.pedidos[-1]

    def urls(self) -> list[str]:
        return [p["url"] for p in self.pedidos]

    def rotas(self) -> list[str]:
        return [p["rota"] for p in self.pedidos]

    # -- context manager ---------------------------------------------
    def __enter__(self) -> "HTTPFalso":
        def _fake_urlopen(req, timeout=None, *args, **kwargs):
            url = getattr(req, "full_url", None) or str(req)
            payload = None
            corpo = getattr(req, "data", None)
            if corpo:
                try:
                    payload = json.loads(corpo.decode("utf-8"))
                except Exception:
                    payload = corpo
            self.pedidos.append({
                "url": url,
                "rota": url.split("127.0.0.1:8000")[-1] if "127.0.0.1:8000" in url else url,
                "payload": payload,
                "timeout": timeout,
                "metodo": getattr(req, "method", None) or getattr(req, "get_method", lambda: None)(),
            })
            if self.erro is not None:
                raise self.erro
            resposta = self.resposta
            if callable(resposta):
                resposta = resposta(url, payload)
            return resposta

        self._patch = mock.patch("urllib.request.urlopen", _fake_urlopen)
        self._patch.start()
        return self

    def __exit__(self, *exc) -> bool:
        if self._patch is not None:
            self._patch.stop()
        return False


# ============================================================
# FastAPI TestClient
# ============================================================

def importar_agent():
    """Importa o agent.py uma unica vez (o import tem efeitos de modulo)."""
    import agent  # noqa: PLC0415
    return agent


def cliente_agent():
    """TestClient do backend, sem abrir portas reais."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    return TestClient(importar_agent().app)


# ============================================================
# Utilitarios de verificacao
# ============================================================

def eh_erro_estruturado(resultado) -> bool:
    """True se o resultado for um dict de erro no formato do projeto."""
    return isinstance(resultado, dict) and resultado.get("status") == "erro"


def sem_excecao(fn, *args, **kwargs):
    """Chama fn e falha com mensagem clara se ela levantar excecao."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"{getattr(fn, '__name__', fn)} levantou {type(exc).__name__}: {exc}"
        ) from exc


class CasoBase(unittest.TestCase):
    """Base com isolamento de ambiente automatico por teste."""

    def setUp(self) -> None:
        self._ambiente = AmbienteIsolado()
        self.tmp = self._ambiente.__enter__()

    def tearDown(self) -> None:
        self._ambiente.__exit__(None, None, None)
