# -*- coding: utf-8 -*-
"""Vision Locate - acha elementos na tela por descricao textual.

Pipeline:
  1. Screenshot (mss)
  2. RapidOCR (detecta todos os textos + bboxes)
  3. Fuzzy match com a descricao (rapido)
  4. Se ambiguo: Qwen3.5 escolhe (LLM)
  5. Retorna coordenadas do centro da bbox
"""
from __future__ import annotations

import os
import json
import base64
import urllib.request
from difflib import SequenceMatcher


SCREENSHOTS_DIR = r"C:\computer-agent\screenshots"
LLM_EYES_URL = os.environ.get("LLM_EYES_URL", "http://127.0.0.1:8081/v1/chat/completions")
LLM_EYES_MODEL = os.environ.get("LLM_EYES_MODEL", "Qwen3.5-0.8B")

# Limiares
FUZZY_THRESHOLD = 0.75      # acima disso, aceita direto
AMBIGUOUS_LOW = 0.3        # abaixo disso, nao tenta LLM (nao vale)
AMBIGUOUS_HIGH = 0.75       # entre LOW e HIGH, chama LLM
MAX_CANDIDATOS_LLM = 10     # manda no maximo 10 pro LLM


def _screenshot() -> dict:
    """Tira screenshot da tela. Retorna dict com path."""
    import datetime
    import mss
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(SCREENSHOTS_DIR, f"vision_{timestamp}.png")
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        mss.tools.to_png(img.rgb, img.size, output=caminho)
    return {"path": caminho, "width": img.width, "height": img.height}


def _ocr(imagem_path: str) -> list:
    """Roda RapidOCR. Retorna lista de {label, bbox, conf}."""
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    resultado, _ = ocr(imagem_path)
    if not resultado:
        return []
    # Palavras que indicam ruido (terminal, debug, logs) - case-insensitive
    RUIDO = ["[vision_locate]", "[teste]", "[ok]", "[aviso]", "[erro]",
             "ps c:\\", "python.exe", ".py\"", ">>>", "<<<",
             "procurando:", "resultado:", "status:", "encontrado:"]

    elementos = []
    for item in resultado:
        bbox_points, texto, conf = item
        texto_lower = texto.lower()
        if any(r in texto_lower for r in RUIDO):
            continue
        xs = [p[0] for p in bbox_points]
        ys = [p[1] for p in bbox_points]
        elementos.append({
            "label": texto,
            "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
            "conf": round(float(conf), 3),
        })
    return elementos


def _similaridade(a: str, b: str) -> float:
    """Similaridade fuzzy entre 2 strings (0-1)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _fuzzy_match(descricao: str, elementos: list) -> tuple:
    """Retorna (melhor_elemento, similaridade). Se lista vazia, retorna (None, 0)."""
    if not elementos:
        return None, 0.0
    melhor = max(elementos, key=lambda e: _similaridade(descricao, e["label"]))
    sim = _similaridade(descricao, melhor["label"])
    return melhor, sim


def _llm_escolher(descricao: str, candidatos: list) -> dict:
    """Manda lista pro Qwen3.5 escolher. Retorna o elemento escolhido ou None."""
    if not candidatos:
        return None

    # Lista os candidatos em formato legivel
    lista = "\n".join(f"{i}. '{c['label']}'" for i, c in enumerate(candidatos))

    prompt = (
        f"Voce e um assistente que escolhe qual elemento da tela clicar.\n\n"
        f"O usuario quer clicar em: '{descricao}'\n\n"
        f"Elementos visiveis na tela:\n{lista}\n\n"
        f"INSTRUCOES:\n"
        f"1. Analise o SIGNIFICADO de cada texto, nao apenas as palavras\n"
        f"2. Escolha o numero do elemento que MELHOR corresponde semanticamente\n"
        f"3. Responda APENAS com o numero, sem explicacao\n\n"
        f"Exemplos:\n"
        f"- Se usuario quer 'botao de login' e existe 'Sign In', responda o numero do 'Sign In'\n"
        f"- Se usuario quer 'criar nova conversa' e existe 'New Chat', responda o numero do 'New Chat'\n"
        f"- Se usuario quer 'pesquisar' e existe 'Search', responda o numero do 'Search'\n\n"
        f"Resposta (apenas o numero):"
    )

    OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
    OLLAMA_MODEL = "qwen2.5:7b"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 10},
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
        print(f"[VISION_LOCATE] LLM respondeu: {texto!r}")
        # Extrai primeiro numero
        import re
        m = re.search(r"\d+", texto)
        if not m:
            return None
        idx = int(m.group())
        if 0 <= idx < len(candidatos):
            return candidatos[idx]
    except Exception as e:
        print(f"[VISION_LOCATE] LLM falhou: {e}")
    return None


def vision_locate(descricao: str, screenshot_path: str = None) -> dict:
    """
    Acha um elemento na tela pela descricao textual.
    
    Args:
        descricao: texto do elemento (ex: "New Chat", "botao de login")
        screenshot_path: caminho de screenshot existente (opcional)
    
    Returns:
        {
            "status": "ok" | "erro",
            "result": str,          # descricao legivel
            "encontrado": bool,
            "x": int, "y": int,     # centro da bbox
            "bbox": [x1, y1, x2, y2],
            "label": str,           # texto que bateu
            "conf": float,          # similaridade
            "screenshot": str,      # caminho do screenshot
            "metodo": "fuzzy" | "llm" | "none"
        }
    """
    if not descricao or not descricao.strip():
        return {"status": "erro", "result": "Descricao vazia"}

    descricao = descricao.strip()

    # 1. Screenshot
    if screenshot_path and os.path.exists(screenshot_path):
        ss = {"path": screenshot_path}
    else:
        try:
            ss = _screenshot()
        except Exception as e:
            return {"status": "erro", "result": f"Erro ao capturar tela: {e}"}

    # 2. OCR
    try:
        elementos = _ocr(ss["path"])
    except Exception as e:
        return {"status": "erro", "result": f"Erro no OCR: {e}"}

    if not elementos:
        return {
            "status": "ok",
            "result": "Nenhum texto detectado na tela",
            "encontrado": False,
            "screenshot": ss["path"],
            "metodo": "none",
        }

    print(f"[VISION_LOCATE] '{descricao}' - {len(elementos)} textos detectados")

    # 3. Fuzzy match
    melhor, sim = _fuzzy_match(descricao, elementos)
    print(f"[VISION_LOCATE] Fuzzy: '{melhor['label']}' (sim={sim:.3f})")

    escolhido = None
    metodo = "none"

    if sim >= FUZZY_THRESHOLD:
        escolhido = melhor
        metodo = "fuzzy"
    elif sim >= AMBIGUOUS_LOW:
        # Zona ambigua: chama LLM
        # Ordena por posicao Y (topo -> baixo) pra nao enviesar o LLM
        candidatos = sorted(elementos, key=lambda e: e["bbox"][1])[:MAX_CANDIDATOS_LLM]
        print(f"[VISION_LOCATE] Ambiguo (sim={sim:.3f}), chamando LLM com {len(candidatos)} candidatos")
        for i, c in enumerate(candidatos):
            print(f"  [{i}] {c['label']!r} @ {c['bbox']}")
        escolhido = _llm_escolher(descricao, candidatos)
        if escolhido:
            metodo = "llm"

    if not escolhido:
        return {
            "status": "ok",
            "result": f"Nenhum elemento corresponde a '{descricao}'",
            "encontrado": False,
            "screenshot": ss["path"],
            "metodo": "none",
        }

    # 4. Calcula centro
    bbox = escolhido["bbox"]
    x = (bbox[0] + bbox[2]) // 2
    y = (bbox[1] + bbox[3]) // 2

    return {
        "status": "ok",
        "result": f"Encontrado '{escolhido['label']}' em ({x}, {y})",
        "encontrado": True,
        "x": x,
        "y": y,
        "bbox": bbox,
        "label": escolhido["label"],
        "conf": escolhido["conf"],
        "screenshot": ss["path"],
        "metodo": metodo,
    }


def vision_click(descricao: str) -> dict:
    """Localiza um elemento e clica no centro dele."""
    loc = vision_locate(descricao)
    if loc.get("status") != "ok" or not loc.get("encontrado"):
        return loc

    try:
        import pyautogui
        pyautogui.click(loc["x"], loc["y"])
        return {
            "status": "ok",
            "result": f"Clicado em '{loc['label']}' ({loc['x']}, {loc['y']})",
            "x": loc["x"],
            "y": loc["y"],
            "label": loc["label"],
            "screenshot": loc["screenshot"],
            "metodo": loc["metodo"],
        }
    except Exception as e:
        return {"status": "erro", "result": f"Erro ao clicar: {e}"}


def vision_type(descricao: str, texto: str, limpar: bool = True) -> dict:
    """Localiza um campo, clica nele e digita."""
    loc = vision_locate(descricao)
    if loc.get("status") != "ok" or not loc.get("encontrado"):
        return loc

    try:
        import pyautogui
        pyautogui.click(loc["x"], loc["y"])
        import time
        time.sleep(0.2)
        if limpar:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
        pyautogui.write(texto, interval=0.02)
        return {
            "status": "ok",
            "result": f"Digitado em '{loc['label']}' ({loc['x']}, {loc['y']})",
            "x": loc["x"],
            "y": loc["y"],
            "label": loc["label"],
            "texto": texto,
        }
    except Exception as e:
        return {"status": "erro", "result": f"Erro ao digitar: {e}"}


# ============================================================
# Auto-teste (roda quando chamado direto)
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        descricao = " ".join(sys.argv[1:])
    else:
        descricao = "New Chat"

    print(f"[TESTE] Procurando: '{descricao}'")
    print("")

    resultado = vision_locate(descricao)
    print("")
    print("Resultado:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))