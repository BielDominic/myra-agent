"""Acesso controlado a controles de janelas via Windows UI Automation."""
from __future__ import annotations

from typing import Any

_MAX_CONTROLES = 200
_ACOES = {"click", "set_text", "focus", "toggle", "select"}


def _backend():
    try:
        from pywinauto import Desktop
        return Desktop(backend="uia")
    except ImportError:
        return None


def _janela(desktop, titulo: str):
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > 200:
        return None, {"status": "erro", "result": "Informe um título de janela válido (1–200 caracteres)."}
    try:
        janelas = [w for w in desktop.windows() if w.is_visible() and titulo.casefold() in (w.window_text() or "").casefold()]
    except Exception as exc:
        return None, {"status": "erro", "result": f"Falha ao enumerar janelas: {type(exc).__name__}: {exc}"}
    if not janelas:
        return None, {"status": "erro", "result": f"Nenhuma janela visível corresponde a {titulo!r}."}
    if len(janelas) > 1:
        return None, {"status": "ambiguous", "result": [w.window_text() for w in janelas[:20]], "message": "Mais de uma janela corresponde; use um título mais específico."}
    return janelas[0], None


def listar_controles(titulo: str, limite: int = 100) -> dict:
    """Lista controles visíveis/identificáveis de uma única janela."""
    if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= _MAX_CONTROLES:
        return {"status": "erro", "result": f"limite deve estar entre 1 e {_MAX_CONTROLES}."}
    desktop = _backend()
    if desktop is None:
        return {"status": "erro", "result": "UI Automation indisponível: instale a dependência pywinauto no ambiente da MYRA."}
    janela, erro = _janela(desktop, titulo)
    if erro:
        return erro
    try:
        controles = []
        for c in janela.descendants():
            if len(controles) >= limite:
                break
            try:
                info = c.element_info
                nome = (info.name or "").strip()
                tipo = info.control_type or ""
                aid = info.automation_id or ""
                if not (nome or aid):
                    continue
                controles.append({
                    "nome": nome[:300], "control_type": tipo[:80],
                    "automation_id": aid[:160],
                    "enabled": bool(c.is_enabled()), "visible": bool(c.is_visible()),
                })
            except Exception:
                continue
        return {"status": "ok", "janela": janela.window_text(), "total": len(controles), "result": controles}
    except Exception as exc:
        return {"status": "erro", "result": f"Falha ao ler controles: {type(exc).__name__}: {exc}"}


def acionar_controle(titulo: str, alvo: str, acao: str, texto: str = "") -> dict:
    """Executa apenas uma ação de UIA permitida em um controle único."""
    if not isinstance(alvo, str) or not alvo.strip() or len(alvo) > 300:
        return {"status": "erro", "result": "Informe nome ou automation_id válido (1–300 caracteres)."}
    if acao not in _ACOES:
        return {"status": "erro", "result": f"Ação não permitida. Use: {', '.join(sorted(_ACOES))}."}
    if acao == "set_text" and (not isinstance(texto, str) or len(texto) > 10000):
        return {"status": "erro", "result": "Texto deve ter até 10.000 caracteres."}
    desktop = _backend()
    if desktop is None:
        return {"status": "erro", "result": "UI Automation indisponível: instale a dependência pywinauto no ambiente da MYRA."}
    janela, erro = _janela(desktop, titulo)
    if erro:
        return erro
    try:
        controles = []
        for c in janela.descendants():
            try:
                info = c.element_info
                nome = str(info.name or "").casefold()
                automation_id = str(info.automation_id or "").casefold()
                controles.append((c, nome, automation_id))
            except Exception:
                continue

        alvo_normalizado = alvo.casefold()
        candidatos = [
            c for c, nome, automation_id in controles
            if alvo_normalizado in {nome, automation_id}
        ]
        # Alguns apps WinUI alteram dinamicamente o nome acessivel do mesmo
        # controle entre a listagem e o clique. Permita substring somente como
        # fallback e apenas se o resultado continuar unico; nunca clique em
        # controles ambiguos.
        if not candidatos:
            candidatos = [
                c for c, nome, automation_id in controles
                if alvo_normalizado in nome or (automation_id and alvo_normalizado in automation_id)
            ]
        if not candidatos:
            return {"status": "erro", "result": f"Nenhum controle corresponde a {alvo!r}."}
        if len(candidatos) > 1:
            return {"status": "ambiguous", "result": [{"nome": c.element_info.name, "automation_id": c.element_info.automation_id, "control_type": c.element_info.control_type} for c in candidatos[:20]], "message": "Controle ambíguo; use automation_id ou nome único."}
        c = candidatos[0]
        if not c.is_visible() or not c.is_enabled():
            return {"status": "erro", "result": "O controle está oculto ou desabilitado; nenhuma ação foi executada."}
        if acao == "click":
            c.click_input()
        elif acao == "set_text":
            c.set_edit_text(texto)
        elif acao == "focus":
            c.set_focus()
        elif acao == "toggle":
            c.toggle()
        elif acao == "select":
            c.select()
        return {"status": "ok", "janela": janela.window_text(), "controle": alvo, "acao": acao, "result": "Ação enviada ao controle; o estado final deve ser verificado separadamente."}
    except Exception as exc:
        return {"status": "erro", "result": f"Falha na ação UIA: {type(exc).__name__}: {exc}"}

def gerenciar_janela(titulo: str, acao: str) -> dict:
    """Executa uma ação limitada na janela única e verifica o estado resultante."""
    permitidas = {"minimize", "maximize", "restore", "close"}
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > 200:
        return {"status": "erro", "result": "Informe um título de janela válido."}
    if acao not in permitidas:
        return {"status": "erro", "result": "Ação não permitida. Use minimize, maximize, restore ou close."}
    desktop = _backend()
    if desktop is None:
        return {"status": "erro", "result": "UI Automation indisponível: pywinauto não está instalado."}
    janela, erro = _janela(desktop, titulo)
    if erro:
        return erro
    try:
        if acao == "minimize":
            janela.minimize()
        elif acao == "maximize":
            janela.maximize()
        elif acao == "restore":
            janela.restore()
        elif acao == "close":
            janela.close()
        restantes = [w for w in desktop.windows() if titulo.casefold() in (w.window_text() or "").casefold()]
        if acao == "close":
            fechada = not any(w.is_visible() for w in restantes)
            return {"status": "ok" if fechada else "unverified", "janela": titulo, "acao": acao,
                    "verified": fechada, "result": "Janela fechada." if fechada else "O pedido de fechar foi enviado, mas a janela ainda aparece."}
        if not restantes:
            return {"status": "unverified", "janela": titulo, "acao": acao, "verified": False,
                    "result": "A ação foi enviada, mas a janela não pôde ser reencontrada para verificar."}
        alvo = restantes[0]
        if acao == "minimize":
            verificado = bool(alvo.is_minimized())
        elif acao == "maximize":
            verificado = bool(alvo.is_maximized())
        else:
            verificado = not bool(alvo.is_minimized())
        return {"status": "ok" if verificado else "unverified", "janela": alvo.window_text(),
                "acao": acao, "verified": verificado,
                "result": "Estado da janela verificado." if verificado else "A ação foi enviada, mas o estado final não foi confirmado."}
    except Exception as exc:
        return {"status": "erro", "result": f"Window action failed: {type(exc).__name__}: {exc}"}
