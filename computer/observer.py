# -*- coding: utf-8 -*-
"""Observer multimodal do MYRA: screenshot + resultado da ferramenta.

Tenta avaliar a tela atual pelo servidor visual local (LLM_EYES_URL). Se a
captura ou o modelo visual estiver indisponivel, recorre ao Ollama textual.
Respostas ambiguas nunca confirmam sucesso.
"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.request


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct-q5_K_M")
LLM_EYES_URL = os.environ.get("LLM_EYES_URL", "http://127.0.0.1:8081/v1/chat/completions")
LLM_EYES_MODEL = os.environ.get("LLM_EYES_MODEL", "Qwen3.5-0.8B")
SCREENSHOT_ENABLED = os.environ.get("MYRA_OBSERVER_SCREENSHOT", "1").strip().lower() not in {"0", "false", "no"}


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
    ini, fim = t.find("{"), t.rfind("}")
    if ini >= 0 and fim > ini:
        try:
            data = json.loads(t[ini:fim + 1])
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _resumir_evidencia_ui(resultado) -> str:
    """Preserva evidencias estruturadas de UIA no prompt, sem confundir mudanca com sucesso."""
    if not isinstance(resultado, dict):
        return ""
    candidatos = [resultado]
    aninhado = resultado.get("result")
    if isinstance(aninhado, dict):
        candidatos.append(aninhado)
    resumo = {}
    for item in candidatos:
        for chave in ("mudanca_observavel", "evidencia_antes", "evidencia_depois", "verified", "status"):
            if chave in item:
                resumo[chave] = item[chave]
    if not resumo:
        return ""
    try:
        return json.dumps(resumo, ensure_ascii=False, default=str)[:1400]
    except (TypeError, ValueError):
        return str(resumo)[:1400]


def _bool_estrito(valor):
    """Coage valores comuns, mas deixa respostas textuais ambÃ­guas indeterminadas."""
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    if isinstance(valor, (int, float)) and valor in (0, 1):
        return bool(valor)
    if isinstance(valor, str):
        normalizado = valor.strip().lower()
        if normalizado in {"true", "1", "sim", "yes", "y"}:
            return True
        if normalizado in {"false", "0", "nao", "nÃ£o", "no", "n", ""}:
            return False
        return None
    if isinstance(valor, (list, dict, tuple, set)) and not valor:
        return False
    return None


def _capturar_screenshot_base64() -> str | None:
    """Captura o monitor principal e devolve PNG Base64, sem gravar no disco."""
    try:
        import mss
        from PIL import Image

        with mss.MSS() as capturador:
            monitores = capturador.monitors
            if len(monitores) < 2:
                return None
            captura = capturador.grab(monitores[1])
            imagem = Image.frombytes("RGB", captura.size, captura.rgb)
            imagem.thumbnail((1280, 720))
            buffer = io.BytesIO()
            imagem.save(buffer, format="PNG", optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as e:
        # Ambiente headless, driver indisponÃ­vel ou falha de captura: fallback textual.
        print(f"[OBSERVER] screenshot indisponivel: {type(e).__name__}")
        return None


def _resposta_llm(prompt: str, imagem_b64: str | None = None) -> str:
    """Chama o modelo visual se houver screenshot; depois o modelo textual."""
    if imagem_b64:
        payload_visual = {
            "model": LLM_EYES_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt + "\n\nUse a imagem anexada como evidencia visual principal."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + imagem_b64}},
                ],
            }],
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 250,
            "response_format": {"type": "json_object"},
        }
        try:
            req = urllib.request.Request(
                LLM_EYES_URL,
                data=json.dumps(payload_visual).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read().decode("utf-8"))
            texto = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(texto, list):
                texto = " ".join(str(p.get("text", "")) for p in texto if isinstance(p, dict))
            if _extrair_json(str(texto)):
                return str(texto).strip()
            print("[OBSERVER] resposta visual sem JSON valido; usando fallback textual")
        except Exception as e:
            print(f"[OBSERVER] modelo visual indisponivel: {type(e).__name__}; fallback textual")

    payload_texto = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 200},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload_texto, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read().decode("utf-8"))
    return resp.get("message", {}).get("content", "").strip()


def observar(objetivo: str, acao_anterior: dict | None = None) -> dict:
    """Avalia aÃ§Ã£o, resultado e screenshot atual, com fallback textual seguro."""
    if not objetivo or not objetivo.strip():
        return {"status": "erro", "result": "objetivo vazio"}

    acao_anterior = acao_anterior or {}
    ferramenta = acao_anterior.get("ferramenta", "?")
    args = acao_anterior.get("args", {})
    resultado = acao_anterior.get("resultado", "")
    erro = acao_anterior.get("erro", "")

    # Regra deterministica para browser_search_google (nao depende do LLM).
    if str(acao_anterior.get("ferramenta", "")).startswith("browser_search_google"):
        _res = acao_anterior.get("resultado") or {}
        if isinstance(_res, dict):
            _payload = _res.get("result", _res)
            if not isinstance(_payload, dict):
                _payload = {}
            _url = str((_payload.get("url") or _res.get("url") or "")).strip().lower()
            _title = str((_payload.get("title") or _res.get("title") or "")).strip().lower()
            _status = str(_res.get("status", "")).lower()
            if _status == "ok" and ("google.com/search" in _url or "q=" in _url) and ("pesquisa google" in _title or "google search" in _title):
                return {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "Pesquisa Google confirmada por URL e titulo.", "proximo_passo_sugerido": ""}

    resultado_str = str(resultado)[:800] if resultado else "(vazio)"
    evidencia_ui = _resumir_evidencia_ui(resultado)
    try:
        args_str = json.dumps(args, ensure_ascii=False)[:200] if args else "{}"
    except (TypeError, ValueError):
        args_str = str(args)[:200]
    erro_str = str(erro)[:300] if erro else ""

    prompt = (
        "VocÃª Ã© um avaliador de aÃ§Ãµes de um agente autÃ´nomo.\n"
        "Analise a aÃ§Ã£o, o resultado e a tela atual. NÃ£o assuma que a aÃ§Ã£o funcionou apenas porque foi executada.\n\n"
        f"OBJETIVO DA TASK: {objetivo}\n\n"
        f"ACAO EXECUTADA: {ferramenta}({args_str})\n"
        f"RESULTADO: {resultado_str}\n"
        f"EVIDENCIA ESTRUTURADA UIA (mudanca nao significa objetivo concluido): {evidencia_ui or '(nao disponivel)'}\n"
        "Use evidencia antes/depois para avaliar o estado, mas so confirme o objetivo se a evidencia sustentar explicitamente a conclusao.\n"
        f"ERRO: {erro_str or '(nenhum)'}\n\n"
        "Responda APENAS com JSON puro (nada antes, nada depois, sem markdown):\n"
        '{"sucesso": true/false, "objetivo_atingido": true/false, '
        '"motivo": "explicaÃ§Ã£o curta em 1 frase", '
        '"proximo_passo_sugerido": "o que fazer se nÃ£o atingiu (ou vazio)"}\n\n'
        "JSON:"
    )

    try:
        imagem = _capturar_screenshot_base64() if SCREENSHOT_ENABLED else None
        texto = _resposta_llm(prompt, imagem)
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

    sucesso = _bool_estrito(data.get("sucesso", False))
    atingido = _bool_estrito(data.get("objetivo_atingido", False))
    if sucesso is None or atingido is None:
        return {
            "status": "ok",
            "sucesso": None,
            "objetivo_atingido": None,
            "motivo": str(data.get("motivo", "resposta ambÃ­gua do observer"))[:300],
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
