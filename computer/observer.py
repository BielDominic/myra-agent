# -*- coding: utf-8 -*-
"""Observer - avalia se a acao anterior atingiu o objetivo.

Versao textual: usa o resultado da ferramenta + o LLM (qwen2.5:7b)
pra decidir se a acao foi bem-sucedida e se o objetivo foi atingido.

Nao tira screenshot. Rapido (~1-2s por chamada).
"""
from __future__ import annotations

import os
import json
import urllib.request


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def _extrair_json(texto: str) -> dict | None:
    """Extrai JSON de uma resposta que pode ter markdown ou texto extra."""
    if not texto:
        return None
    t = texto.strip()
    # Remove blocos markdown ```json ... ```
    if t.startswith("```"):
        linhas = t.split("\n")
        if linhas[0].startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].strip().startswith("```"):
            linhas = linhas[:-1]
        t = "\n".join(linhas).strip()
    # Tenta achar primeiro { e ultimo }
    ini = t.find("{")
    fim = t.rfind("}")
    if ini >= 0 and fim > ini:
        try:
            return json.loads(t[ini:fim+1])
        except Exception:
            pass
    return None


def observar(objetivo: str, acao_anterior: dict = None) -> dict:
    """
    Avalia se a acao anterior atingiu o objetivo.

    Args:
        objetivo: o que a task ta tentando fazer
        acao_anterior: {ferramenta, args, resultado, erro} da acao anterior

    Returns:
        {
            "status": "ok" | "erro",
            "sucesso": bool,           # a acao funcionou?
            "objetivo_atingido": bool, # o objetivo foi completado?
            "motivo": str,             # explicacao curta
            "proximo_passo_sugerido": str,  # se nao atingiu, o que fazer
        }
    """
    if not objetivo:
        return {"status": "erro", "result": "objetivo vazio"}

    ferramenta = (acao_anterior or {}).get("ferramenta", "?")
    args = (acao_anterior or {}).get("args", {})
    resultado = (acao_anterior or {}).get("resultado", "")
    erro = (acao_anterior or {}).get("erro", "")

    # Trunca pra nao estourar contexto
    resultado_str = str(resultado)[:800] if resultado else "(vazio)"
    args_str = json.dumps(args, ensure_ascii=False)[:200] if args else "{}"
    erro_str = str(erro)[:300] if erro else ""

    prompt = (
        f"Voce e um avaliador de acoes de um agente autonomo.\\n"
        f"Analise a acao executada e diga se funcionou e se o objetivo foi atingido.\\n\\n"
        f"OBJETIVO DA TASK: {objetivo}\\n\\n"
        f"ACAO EXECUTADA: {ferramenta}({args_str})\\n"
        f"RESULTADO: {resultado_str}\\n"
        f"ERRO: {erro_str or '(nenhum)'}\\n\\n"
        f"Responda APENAS com JSON puro (nada antes, nada depois, sem markdown):\\n"
        f'{{"sucesso": true/false, "objetivo_atingido": true/false, '
        f'"motivo": "explicacao curta em 1 frase", '
        f'"proximo_passo_sugerido": "o que fazer se nao atingiu (ou vazio)"}}\\n\\n'
        f"JSON:"
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        texto = resp.get("message", {}).get("content", "").strip()
    except Exception as e:
        return {
            "status": "erro",
            "result": f"erro ao chamar LLM: {e}",
        }

    # Parseia
    data = _extrair_json(texto)
    if not data:
        # Fallback: usa o texto cru como motivo
        return {
            "status": "ok",
            "sucesso": None,
            "objetivo_atingido": None,
            "motivo": texto[:300] if texto else "(sem resposta)",
            "proximo_passo_sugerido": "",
            "raw": texto[:500],
        }

    return {
        "status": "ok",
        "sucesso": bool(data.get("sucesso", False)),
        "objetivo_atingido": bool(data.get("objetivo_atingido", False)),
        "motivo": str(data.get("motivo", ""))[:300],
        "proximo_passo_sugerido": str(data.get("proximo_passo_sugerido", ""))[:300],
    }


# ============================================================
# Auto-teste
# ============================================================
if __name__ == "__main__":
    import sys

    objetivo = "criar nova conversa no Open WebUI"
    acao = {
        "ferramenta": "browser_click_text",
        "args": {"text": "New Chat"},
        "resultado": {"ok": True, "clicked": "New Chat"},
        "erro": None,
    }

    print(f"[TESTE] Objetivo: {objetivo}")
    print(f"[TESTE] Acao: {acao['ferramenta']}({acao['args']})")
    print("")

    r = observar(objetivo, acao)
    print(json.dumps(r, indent=2, ensure_ascii=False))