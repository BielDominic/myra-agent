# -*- coding: utf-8 -*-
"""Observer textual do MYRA: avalia a acao anterior com evidencias.

A versao atual usa o resultado da ferramenta e o modelo textual do Ollama.
O contrato aceita apenas booleanos JSON reais (nao transforma a string
"false" em True), e uma resposta ambigua nunca pode confirmar sucesso.
"""
from __future__ import annotations

import json
import os
import urllib.request


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def _extrair_json(texto: str) -> dict | None:
    """Extrai JSON de uma resposta que pode ter markdown ou texto extra."""
    if not texto:
        return None
    t = texto.strip()
    if t.startswith("```"):
        linhas = t.split("\n")
        if linhas[0].startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].strip().startswith("```"):
            linhas = linhas[:-1]
        t = "\n".join(linhas).strip()
    ini = t.find("{")
    fim = t.rfind("}")
    if ini >= 0 and fim > ini:
        try:
            data = json.loads(t[ini:fim + 1])
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _bool_estrito(valor):
    """Retorna bool apenas para booleanos reais ou strings inequívocas."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        normalizado = valor.strip().lower()
        if normalizado == "true":
            return True
        if normalizado == "false":
            return False
    return None


def observar(objetivo: str, acao_anterior: dict | None = None) -> dict:
    """Avalia se a ação anterior funcionou e se concluiu o objetivo."""
    if not objetivo or not objetivo.strip():
        return {"status": "erro", "result": "objetivo vazio"}

    acao_anterior = acao_anterior or {}
    ferramenta = acao_anterior.get("ferramenta", "?")
    args = acao_anterior.get("args", {})
    resultado = acao_anterior.get("resultado", "")
    erro = acao_anterior.get("erro", "")

    resultado_str = str(resultado)[:800] if resultado else "(vazio)"
    try:
        args_str = json.dumps(args, ensure_ascii=False)[:200] if args else "{}"
    except (TypeError, ValueError):
        args_str = str(args)[:200]
    erro_str = str(erro)[:300] if erro else ""

    prompt = (
        "Você é um avaliador de ações de um agente autônomo.\n"
        "Analise a ação executada e diga se funcionou e se o objetivo foi atingido.\n\n"
        f"OBJETIVO DA TASK: {objetivo}\n\n"
        f"AÇÃO EXECUTADA: {ferramenta}({args_str})\n"
        f"RESULTADO: {resultado_str}\n"
        f"ERRO: {erro_str or '(nenhum)'}\n\n"
        "Responda APENAS com JSON puro (nada antes, nada depois, sem markdown):\n"
        '{"sucesso": true/false, "objetivo_atingido": true/false, '
        '"motivo": "explicação curta em 1 frase", '
        '"proximo_passo_sugerido": "o que fazer se não atingiu (ou vazio)"}\n\n'
        "JSON:"
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
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode("utf-8"))
        texto = resp.get("message", {}).get("content", "").strip()
    except Exception as e:
        return {"status": "erro", "result": f"erro ao chamar LLM: {type(e).__name__}: {e}"}

    data = _extrair_json(texto)
    if not data:
        return {
            "status": "ok",
            "sucesso": None,
            "objetivo_atingido": None,
            "motivo": texto[:300] if texto else "(sem resposta)",
            "proximo_passo_sugerido": "",
            "raw": texto[:500],
        }

    sucesso = _bool_estrito(data.get("sucesso"))
    atingido = _bool_estrito(data.get("objetivo_atingido"))
    # Resposta incompleta/ambígua não pode ser convertida em sucesso.
    if sucesso is None or atingido is None:
        return {
            "status": "ok",
            "sucesso": None,
            "objetivo_atingido": None,
            "motivo": str(data.get("motivo", "resposta ambígua do observer"))[:300],
            "proximo_passo_sugerido": str(data.get("proximo_passo_sugerido", ""))[:300],
            "raw": texto[:500],
        }

    return {
        "status": "ok",
        "sucesso": sucesso,
        "objetivo_atingido": atingido,
        "motivo": str(data.get("motivo", ""))[:300],
        "proximo_passo_sugerido": str(data.get("proximo_passo_sugerido", ""))[:300],
    }


if __name__ == "__main__":
    objetivo = "abrir o GitHub no navegador"
    acao = {
        "ferramenta": "browser_new_tab",
        "args": {"url": "https://github.com"},
        "resultado": {"status": "ok", "result": "aba aberta"},
        "erro": None,
    }
    print(json.dumps(observar(objetivo, acao), indent=2, ensure_ascii=False))
