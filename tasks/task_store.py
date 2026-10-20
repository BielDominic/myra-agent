# -*- coding: utf-8 -*-
"""FASE 26 - persistencia de tasks do MYRA (SQLite).

Guarda objetivo, passo atual, historico, estado e timestamps de cada task
para permitir:

- retomar uma task depois de pausa (pausa/continua sem perder contexto);
- retomar uma task depois de crash/reinicio do MYRA (estado "interrompido");
- consultar o historico de execucao por task.

O banco fica, por padrao, em %LOCALAPPDATA%\\MYRA\\myra_tasks.sqlite3 e pode
ser redirecionado por MYRA_TASK_DB (usado nos testes).

Nada aqui chama LLM, rede ou ferramentas: e somente persistencia.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

# ------------------------------------------------------------
# Estados possiveis de uma task
# ------------------------------------------------------------

ESTADO_EM_EXECUCAO = "em_execucao"
ESTADO_PAUSADO = "pausado"
ESTADO_INTERROMPIDO = "interrompido"
ESTADO_CANCELADO = "cancelado"
ESTADO_CONCLUIDO = "concluido"
ESTADO_FALHOU = "falhou"

ESTADOS_FINAIS = (ESTADO_CANCELADO, ESTADO_CONCLUIDO, ESTADO_FALHOU)
ESTADOS_RETOMAVEIS = (ESTADO_EM_EXECUCAO, ESTADO_PAUSADO, ESTADO_INTERROMPIDO)

# Identificador desta execucao do processo. Permite distinguir tasks que
# ficaram "em_execucao" de um processo morto das tasks deste processo.
RUN_ID = uuid.uuid4().hex[:12]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id         TEXT PRIMARY KEY,
    objetivo        TEXT NOT NULL,
    max_passos      INTEGER NOT NULL DEFAULT 15,
    passo_atual     INTEGER NOT NULL DEFAULT 0,
    estado          TEXT NOT NULL,
    historico       TEXT NOT NULL DEFAULT '[]',
    resultado_final TEXT,
    erro            TEXT,
    run_id          TEXT,
    criado_em       REAL NOT NULL,
    atualizado_em   REAL NOT NULL,
    terminado_em    REAL
);

CREATE TABLE IF NOT EXISTS task_eventos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id   TEXT NOT NULL,
    passo     INTEGER,
    tipo      TEXT NOT NULL,
    detalhe   TEXT,
    criado_em REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_estado ON tasks (estado);
CREATE INDEX IF NOT EXISTS idx_eventos_task ON task_eventos (task_id);
"""

_lock = threading.RLock()
_initialized_paths: set[str] = set()


# ------------------------------------------------------------
# Conexao
# ------------------------------------------------------------

def _database_path() -> Path:
    configurado = os.environ.get("MYRA_TASK_DB", "").strip()
    if configurado:
        path = Path(configurado).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_app_data) / "MYRA" if local_app_data else Path.home() / ".myra"
        path = base / "myra_tasks.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    # O esquema e garantido por caminho de banco (MYRA_TASK_DB pode mudar
    # entre execucoes, o que e usado nos testes).
    caminho = str(_database_path())
    conn = sqlite3.connect(caminho, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        if caminho not in _initialized_paths:
            with _lock:
                if caminho not in _initialized_paths:
                    conn.executescript(_SCHEMA)
                    conn.commit()
                    _initialized_paths.add(caminho)
    except Exception:
        conn.close()
        raise
    return conn


def db_path() -> str:
    """Caminho do banco em uso (util para diagnostico e testes)."""
    return str(_database_path())


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _agora() -> float:
    return time.time()


def novo_task_id() -> str:
    return f"task-{int(time.time())}-{uuid.uuid4().hex[:8]}"


def _dumps(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def _loads(texto, default):
    if not texto:
        return default
    try:
        return json.loads(texto)
    except Exception:
        return default


def _row_para_dict(row: sqlite3.Row, com_historico: bool = True) -> dict:
    dados = {
        "task_id": row["task_id"],
        "objetivo": row["objetivo"],
        "max_passos": row["max_passos"],
        "passo_atual": row["passo_atual"],
        "estado": row["estado"],
        "resultado_final": row["resultado_final"],
        "erro": row["erro"],
        "run_id": row["run_id"],
        "criado_em": row["criado_em"],
        "atualizado_em": row["atualizado_em"],
        "terminado_em": row["terminado_em"],
    }
    if com_historico:
        dados["historico"] = _loads(row["historico"], [])
    return dados


# ------------------------------------------------------------
# API principal
# ------------------------------------------------------------

def criar_task(objetivo: str, max_passos: int = 15, task_id: str | None = None) -> dict:
    """Cria (ou recria) o registo de uma task e devolve o dict persistido."""
    if not objetivo or not str(objetivo).strip():
        raise ValueError("objetivo vazio")
    tid = task_id or novo_task_id()
    agora = _agora()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO tasks (task_id, objetivo, max_passos, passo_atual, estado,
                                   historico, resultado_final, erro, run_id,
                                   criado_em, atualizado_em, terminado_em)
                VALUES (?, ?, ?, 0, ?, '[]', NULL, NULL, ?, ?, ?, NULL)
                ON CONFLICT(task_id) DO UPDATE SET
                    objetivo = excluded.objetivo,
                    max_passos = excluded.max_passos,
                    estado = excluded.estado,
                    run_id = excluded.run_id,
                    atualizado_em = excluded.atualizado_em
                """,
                (tid, str(objetivo), int(max_passos), ESTADO_EM_EXECUCAO, RUN_ID, agora, agora),
            )
            conn.commit()
        finally:
            conn.close()
    return carregar_task(tid)


def salvar_task(
    task_id: str,
    *,
    passo_atual: int | None = None,
    estado: str | None = None,
    historico: list | None = None,
    resultado_final: str | None = None,
    erro: str | None = None,
    terminado: bool = False,
) -> dict | None:
    """Atualiza os campos informados de uma task. Campos None sao ignorados.

    terminado=True grava terminado_em e limpa erro quando o estado e final
    bem-sucedido. Retorna a task atualizada ou None se ela nao existir.
    """
    if not task_id:
        return None

    campos = ["atualizado_em = ?"]
    valores: list = [_agora()]

    if passo_atual is not None:
        campos.append("passo_atual = ?")
        valores.append(int(passo_atual))
    if estado is not None:
        campos.append("estado = ?")
        valores.append(str(estado))
    if historico is not None:
        campos.append("historico = ?")
        valores.append(_dumps(historico))
    if resultado_final is not None:
        campos.append("resultado_final = ?")
        valores.append(str(resultado_final))
    if erro is not None:
        campos.append("erro = ?")
        valores.append(str(erro))
    if terminado:
        campos.append("terminado_em = ?")
        valores.append(_agora())

    valores.append(task_id)

    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                f"UPDATE tasks SET {', '.join(campos)} WHERE task_id = ?", valores
            )
            conn.commit()
            alterou = cur.rowcount
        finally:
            conn.close()

    if not alterou:
        return None
    return carregar_task(task_id)


def registrar_evento(
    task_id: str, tipo: str, detalhe: str = "", passo: int | None = None
) -> None:
    """Grava um evento de auditoria da task (inicio, passo, recuperacao, erro...)."""
    if not task_id:
        return
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO task_eventos (task_id, passo, tipo, detalhe, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (task_id, passo, str(tipo), str(detalhe)[:2000], _agora()),
            )
            conn.commit()
        finally:
            conn.close()


def listar_eventos(task_id: str, limite: int = 100) -> list[dict]:
    with _lock:
        conn = _connect()
        try:
            linhas = conn.execute(
                "SELECT passo, tipo, detalhe, criado_em FROM task_eventos "
                "WHERE task_id = ? ORDER BY id ASC LIMIT ?",
                (task_id, int(limite)),
            ).fetchall()
        finally:
            conn.close()
    return [dict(linha) for linha in linhas]


def carregar_task(task_id: str) -> dict | None:
    """Carrega uma task com historico desserializado."""
    if not task_id:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        finally:
            conn.close()
    return _row_para_dict(row) if row else None


def listar_tasks(estado: str | None = None, limite: int = 20) -> list[dict]:
    """Lista tasks recentes (sem historico, para resposta leve)."""
    with _lock:
        conn = _connect()
        try:
            if estado:
                linhas = conn.execute(
                    "SELECT * FROM tasks WHERE estado = ? "
                    "ORDER BY atualizado_em DESC LIMIT ?",
                    (estado, int(limite)),
                ).fetchall()
            else:
                linhas = conn.execute(
                    "SELECT * FROM tasks ORDER BY atualizado_em DESC LIMIT ?",
                    (int(limite),),
                ).fetchall()
        finally:
            conn.close()
    return [_row_para_dict(linha, com_historico=False) for linha in linhas]


def tasks_retomaveis(limite: int = 20) -> list[dict]:
    """Tasks que podem ser retomadas (em execucao, pausadas ou interrompidas)."""
    marcadores = ",".join("?" for _ in ESTADOS_RETOMAVEIS)
    with _lock:
        conn = _connect()
        try:
            linhas = conn.execute(
                f"SELECT * FROM tasks WHERE estado IN ({marcadores}) "
                "ORDER BY atualizado_em DESC LIMIT ?",
                (*ESTADOS_RETOMAVEIS, int(limite)),
            ).fetchall()
        finally:
            conn.close()
    return [_row_para_dict(linha, com_historico=False) for linha in linhas]


def marcar_interrompidas(
    motivo: str = "processo interrompido (crash ou reinicio do MYRA)",
    run_id: str | None = None,
) -> int:
    """Marca como 'interrompido' as tasks 'em_execucao' de execucoes anteriores.

    Deve ser chamada uma vez no startup do agent.py. Tasks deste proprio
    processo (mesmo run_id) sao preservadas.
    Retorna quantas tasks foram marcadas.
    """
    atual = run_id if run_id is not None else RUN_ID
    agora = _agora()
    with _lock:
        conn = _connect()
        try:
            linhas = conn.execute(
                "SELECT task_id FROM tasks WHERE estado = ? "
                "AND (run_id IS NULL OR run_id != ?)",
                (ESTADO_EM_EXECUCAO, atual),
            ).fetchall()
            ids = [linha["task_id"] for linha in linhas]
            for tid in ids:
                conn.execute(
                    "UPDATE tasks SET estado = ?, erro = ?, atualizado_em = ? "
                    "WHERE task_id = ?",
                    (ESTADO_INTERROMPIDO, motivo, agora, tid),
                )
                conn.execute(
                    "INSERT INTO task_eventos (task_id, passo, tipo, detalhe, criado_em) "
                    "VALUES (?, NULL, ?, ?, ?)",
                    (tid, "interrompida", motivo, agora),
                )
            conn.commit()
        finally:
            conn.close()
    return len(ids)


def apagar_task(task_id: str) -> bool:
    """Remove a task e seus eventos. Usado apenas em limpeza/testes."""
    if not task_id:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.execute("DELETE FROM task_eventos WHERE task_id = ?", (task_id,))
            conn.commit()
            return bool(cur.rowcount)
        finally:
            conn.close()


# ------------------------------------------------------------
# Auto-teste manual: python -m tasks.task_store
# ------------------------------------------------------------
if __name__ == "__main__":
    print(f"[STORE] banco: {db_path()}")
    t = criar_task("teste de persistencia", max_passos=3)
    print(f"[STORE] criada: {t['task_id']} estado={t['estado']}")

    salvar_task(
        t["task_id"],
        passo_atual=1,
        historico=[{"passo": 1, "ferramenta": "get_current_time", "ok": True}],
    )
    registrar_evento(t["task_id"], "passo", "get_current_time", passo=1)
    salvar_task(t["task_id"], estado=ESTADO_PAUSADO)
    print(f"[STORE] pausada: {carregar_task(t['task_id'])['estado']}")
    print(f"[STORE] retomaveis: {[x['task_id'] for x in tasks_retomaveis()]}")
    print(f"[STORE] eventos: {listar_eventos(t['task_id'])}")
    apagar_task(t["task_id"])
    print("[STORE] ok")
