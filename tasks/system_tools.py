# -*- coding: utf-8 -*-
"""Ferramentas de sistema pro planner: arquivos, codigo, email, PC, utilitarias.

Chamadas HTTP pro proprio agent.py (localhost:8000). Seguro contra import circular.
"""
from __future__ import annotations

import json
import urllib.request


API_URL = "http://127.0.0.1:8000"


def _post(rota: str, payload: dict) -> dict:
    """POST pro proprio agent.py."""
    try:
        req = urllib.request.Request(
            API_URL + rota,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


# ============================================================
# ARQUIVOS
# ============================================================

def write_file(caminho: str, conteudo: str) -> dict:
    """Cria ou sobrescreve um arquivo no workspace."""
    return _post("/write_file", {"caminho": caminho, "conteudo": conteudo})


def read_file(caminho: str) -> dict:
    """Le um arquivo do workspace."""
    return _post("/read_file", {"caminho": caminho})


def list_dir(caminho: str = ".") -> dict:
    """Lista arquivos/pastas."""
    return _post("/list_dir", {"caminho": caminho})


def delete_file(caminho: str) -> dict:
    """Apaga um arquivo."""
    return _post("/delete_file", {"caminho": caminho})


def create_dir(caminho: str) -> dict:
    """Cria uma pasta."""
    return _post("/create_dir", {"caminho": caminho})


def move_file(origem: str, destino: str) -> dict:
    """Move/renomeia um arquivo."""
    return _post("/move_file", {"origem": origem, "destino": destino})


def search_in_files(termo: str, extensao: str = ".txt") -> dict:
    """Busca texto em arquivos do workspace."""
    return _post("/search_in_files", {"termo": termo, "extensao": extensao})


# ============================================================
# CODIGO
# ============================================================

def code_run(codigo: str) -> dict:
    """Executa codigo Python e retorna stdout/stderr/exit code."""
    return _post("/code_run", {"codigo": codigo})


def run_python(codigo: str) -> dict:
    """Alias de code_run (mantido pra compatibilidade)."""
    return code_run(codigo)


# ============================================================
# EMAIL
# ============================================================

def email_list(quantidade: int = 5) -> dict:
    """Lista os ultimos emails da caixa de entrada."""
    return _post("/email_list", {"quantidade": quantidade})


def email_read(indice: int = 0) -> dict:
    """Le um email pelo indice."""
    return _post("/email_read", {"indice": indice})


def email_send(para: str, assunto: str, corpo: str) -> dict:
    """Envia um email."""
    return _post("/email_send", {"para": para, "assunto": assunto, "corpo": corpo})


def email_search(termo: str, quantidade: int = 10) -> dict:
    """Busca emails por termo."""
    return _post("/email_search", {"termo": termo, "pasta": "INBOX", "quantidade": quantidade})


def email_reply(indice: int = 0, corpo: str = "") -> dict:
    """Responde um email; o corpo da resposta e obrigatorio e nao pode ficar vazio."""
    if not isinstance(corpo, str) or not corpo.strip():
        return {"status": "erro", "result": "Corpo da resposta obrigatorio."}
    return _post("/email_reply", {"indice": indice, "pasta": "INBOX", "corpo": corpo})


# ============================================================
# PC (mouse, teclado, janelas)
# ============================================================

def pc_move_mouse(x: int, y: int) -> dict:
    """Move o mouse pra (x, y)."""
    return _post("/pc_move_mouse", {"x": x, "y": y, "duration": 0.3})


def pc_click(x: int = None, y: int = None, button: str = "left") -> dict:
    """Clica em (x, y). Se x/y nao passados, clica na posicao atual."""
    payload = {"button": button}
    if x is not None:
        payload["x"] = x
    if y is not None:
        payload["y"] = y
    return _post("/pc_click", payload)


def pc_type_text(text: str) -> dict:
    """Digita texto via teclado do PC."""
    return _post("/pc_type_text", {"text": text, "interval": 0.02})


def pc_press_key(key: str) -> dict:
    """Pressiona uma tecla. Ex: 'enter', 'tab', 'esc'."""
    return _post("/pc_press_key", {"key": key})


def pc_hotkey(keys: list) -> dict:
    """Combinacao de teclas. Ex: ['ctrl', 'c']."""
    return _post("/pc_hotkey", {"keys": keys})


def pc_screenshot() -> dict:
    """Tira screenshot da tela do PC."""
    return _post("/pc_screenshot", {"salvar": True})


def pc_list_applications() -> dict:
    """Lista atalhos de aplicativos no menu Iniciar e desktops do Windows."""
    return _post("/pc_list_applications", {})


def pc_open_application(nome: str) -> dict:
    """Abre um aplicativo por nome de atalho conhecido. Obrigatorio: nome."""
    return _post("/pc_open_application", {"nome": nome})


def pc_uninstall_application(nome: str) -> dict:
    """Desinstala um aplicativo Windows Appx/MSIX por nome."""
    return _post("/pc_uninstall_application", {"nome": nome})


def pc_list_controls(titulo: str, limite: int = 100) -> dict:
    return _post("/pc_list_controls", {"titulo": titulo, "limite": limite})


def pc_control_action(titulo: str, alvo: str, acao: str, texto: str = "") -> dict:
    return _post("/pc_control_action", {"titulo": titulo, "alvo": alvo, "acao": acao, "texto": texto})


def pc_window_action(titulo: str, acao: str) -> dict:
    return _post("/pc_window_action", {"titulo": titulo, "acao": acao})


def pc_get_windows() -> dict:
    """Lista janelas abertas."""
    return _post("/pc_get_windows", {})


def pc_get_active_window() -> dict:
    """Retorna a janela ativa."""
    return _post("/pc_get_active_window", {})


def pc_focus_window(titulo: str) -> dict:
    """Foca uma janela pelo titulo."""
    return _post("/pc_focus_window", {"titulo": titulo})


# ============================================================
# UTILITARIAS
# ============================================================

def get_current_time() -> dict:
    """Data e hora atual."""
    return _post("/get_current_time", {})


def get_weather(cidade: str = "") -> dict:
    """Clima de uma cidade."""
    return _post("/get_weather", {"cidade": cidade})


def save_note(texto: str) -> dict:
    """Salva uma nota."""
    return _post("/save_note", {"texto": texto})


def read_notes() -> dict:
    """Le todas as notas."""
    return _post("/read_notes", {})


# ============================================================
# REGISTRO NO PLANNER
# ============================================================

def registrar_todas(registrar_ferramenta):
    """Registra todas as ferramentas do planner."""

    # --- ARQUIVOS ---
    registrar_ferramenta("write_file", write_file,
        "Cria ou sobrescreve um arquivo no workspace. Obrigatorio: caminho, conteudo.")
    registrar_ferramenta("read_file", read_file,
        "Le um arquivo do workspace. Obrigatorio: caminho.")
    registrar_ferramenta("list_dir", list_dir,
        "Lista arquivos e pastas. Opcional: caminho (default '.').")
    registrar_ferramenta("delete_file", delete_file,
        "Apaga um arquivo do workspace. Obrigatorio: caminho.")
    registrar_ferramenta("create_dir", create_dir,
        "Cria uma pasta. Obrigatorio: caminho.")
    registrar_ferramenta("move_file", move_file,
        "Move ou renomeia um arquivo. Obrigatorio: origem, destino.")
    registrar_ferramenta("search_in_files", search_in_files,
        "Busca texto em arquivos. Obrigatorio: termo. Opcional: extensao (default .txt).")

    # --- CODIGO ---
    registrar_ferramenta("code_run", code_run,
        "Executa codigo Python e retorna stdout/stderr/exit code. Obrigatorio: codigo.")
    registrar_ferramenta("run_python", run_python,
        "Executa codigo Python (alias de code_run). Obrigatorio: codigo.")

    # --- EMAIL ---
    registrar_ferramenta("email_list", email_list,
        "Lista os ultimos emails. Opcional: quantidade (default 5).")
    registrar_ferramenta("email_read", email_read,
        "Le um email pelo indice (0 = mais recente).")
    registrar_ferramenta("email_send", email_send,
        "Envia um email. Obrigatorio: para, assunto, corpo.")
    registrar_ferramenta("email_search", email_search,
        "Busca emails por termo. Obrigatorio: termo. Opcional: quantidade.")
    registrar_ferramenta("email_reply", email_reply,
        "Responde um email. Obrigatorio: corpo. Opcional: indice.")

    # --- PC ---
    registrar_ferramenta("pc_move_mouse", pc_move_mouse,
        "Move o mouse pra (x, y). Obrigatorio: x, y.")
    registrar_ferramenta("pc_click", pc_click,
        "Clica em (x, y). Opcional: x, y, button.")
    registrar_ferramenta("pc_type_text", pc_type_text,
        "Digita texto via teclado do PC. Obrigatorio: text.")
    registrar_ferramenta("pc_press_key", pc_press_key,
        "Pressiona uma tecla. Obrigatorio: key.")
    registrar_ferramenta("pc_hotkey", pc_hotkey,
        "Combinacao de teclas (ex: ['ctrl','c']). Obrigatorio: keys.")
    registrar_ferramenta("pc_screenshot", pc_screenshot,
        "Tira screenshot da tela do PC.")
    registrar_ferramenta("pc_get_windows", pc_get_windows,
        "Lista janelas abertas.")
    registrar_ferramenta("pc_get_active_window", pc_get_active_window,
        "Retorna a janela ativa.")
    registrar_ferramenta("pc_focus_window", pc_focus_window,
        "Foca uma janela pelo titulo. Obrigatorio: titulo.")
    registrar_ferramenta("pc_list_applications", pc_list_applications,
        "Lista aplicativos acess?veis pelos atalhos do menu Iniciar e desktops do Windows.")
    registrar_ferramenta("pc_open_application", pc_open_application,
        "Abre um aplicativo pelo nome do atalho conhecido. Obrigatorio: nome. Se houver nomes ambiguos, escolha um mais especifico.")
    registrar_ferramenta("pc_uninstall_application", pc_uninstall_application,
        "Desinstala um aplicativo Windows Appx/MSIX pelo nome exato ou correspondencia unica; verifica a remocao.")
    registrar_ferramenta("pc_list_controls", pc_list_controls,
        "Lista controles UI Automation de uma janela. Obrigatorio: titulo; opcional limite entre 1 e 200.")
    registrar_ferramenta("pc_control_action", pc_control_action,
        "Aciona um controle UIA unico. Obrigatorios: titulo, alvo, acao; acoes permitidas: click, set_text, focus, toggle, select; texto opcional.")
    registrar_ferramenta("pc_window_action", pc_window_action,
        "Minimiza/maximiza/restaura/fecha uma janela unica. Obrigatorios: titulo, acao (minimize, maximize, restore, close). Fechar pode perder trabalho nao salvo: confirme com o usuario quando houver esse risco.")

    # --- UTILITARIAS ---
    registrar_ferramenta("get_current_time", get_current_time,
        "Retorna data e hora atual.")
    registrar_ferramenta("get_weather", get_weather,
        "Clima de uma cidade. Opcional: cidade.")
    registrar_ferramenta("save_note", save_note,
        "Salva uma nota. Obrigatorio: texto.")
    registrar_ferramenta("read_notes", read_notes,
        "Le todas as notas salvas.")