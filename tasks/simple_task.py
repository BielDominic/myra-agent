"""
FASE 22-light — Task simples com planner + retry.
Sem banco, sem scheduler. So planeja, executa e sintetiza.
"""
import json
import re
import time
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELO_PLANNER = "qwen2.5:7b"

# Ferramentas que o loop pode chamar. Mapeia nome -> funcao Python.
FERRAMENTAS_DISPONIVEIS = {}

# Descricoes de quando usar cada ferramenta.
# Isso ajuda o LLM a escolher a ferramenta certa pra cada objetivo.
FERRAMENTAS_DESCRICOES = {}


def registrar_ferramenta(nome: str, fn, descricao: str = ""):
    """Registra uma ferramenta pro loop poder chamar."""
    FERRAMENTAS_DISPONIVEIS[nome] = fn
    if descricao:
        FERRAMENTAS_DESCRICOES[nome] = descricao


def _llm(prompt: str, system: str = "", timeout: int = 120) -> str:
    """Chama o Ollama e retorna o texto puro."""
    payload = {
        "model": MODELO_PLANNER,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resposta = json.loads(r.read().decode("utf-8"))
    return resposta.get("response", "").strip()


def _extrair_json(texto: str):
    """Extrai o primeiro JSON valido do texto."""
    try:
        return json.loads(texto)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio >= 0 and fim > inicio:
        try:
            return json.loads(texto[inicio:fim + 1])
        except Exception:
            pass
    return None


def _planejar(objetivo: str) -> list:
    """Pede ao LLM um plano de ate 5 passos."""
    if FERRAMENTAS_DESCRICOES:
        nomes = "\n".join(
            f"- {nome}: {FERRAMENTAS_DESCRICOES.get(nome, 'sem descricao')}"
            for nome in sorted(FERRAMENTAS_DISPONIVEIS.keys())
        )
    else:
        nomes = ", ".join(sorted(FERRAMENTAS_DISPONIVEIS.keys()))

    system = (
        "Voce e um planejador de tarefas. Dado um objetivo, voce escolhe "
        "as ferramentas certas e retorna um plano em JSON. "
        "Responda SEMPRE com JSON puro, sem texto antes ou depois."
    )

    prompt = f"""OBJETIVO: {objetivo}

FERRAMENTAS DISPONIVEIS:
{nomes}

REGRAS:
- Maximo 5 passos.
- Cada passo chama UMA ferramenta.
- Escolha a ferramenta MAIS ESPECIFICA para o objetivo.
  Exemplo: se fala de "tempo" ou "clima", use get_weather (nao web_search).
  Exemplo: se fala de "horas" ou "data", use get_current_time (nao web_search).
  Exemplo: se tem URL do YouTube, use youtube_transcript (nao open_url).
- Se o objetivo for simples, use 1 ou 2 passos.
- O ULTIMO passo DEVE ser sempre "responder" para sintetizar.

FORMATO DA RESPOSTA (JSON puro, sem markdown):
{{
  "passos": [
    {{"ferramenta": "nome_da_ferramenta", "args": {{"chave": "valor"}}, "motivo": "por que esse passo"}}
  ]
}}
"""

    texto = _llm(prompt, system)
    data = _extrair_json(texto)

    if not data or "passos" not in data:
        print(f"[TASK] LLM nao retornou JSON valido. Texto cru: {texto[:200]}")
        return [{"ferramenta": "responder", "args": {"pergunta": objetivo}, "motivo": "fallback (JSON invalido)"}]

    passos = data["passos"]
    validos = []
    for p in passos[:5]:
        nome = p.get("ferramenta", "")
        if nome in FERRAMENTAS_DISPONIVEIS:
            validos.append({
                "ferramenta": nome,
                "args": p.get("args", {}) or {},
                "motivo": p.get("motivo", ""),
            })
        else:
            print(f"[TASK] AVISO: LLM escolheu ferramenta invalida: {nome!r}")

    if not validos:
        print("[TASK] Nenhuma ferramenta valida no plano. Usando fallback.")
        return [{"ferramenta": "responder", "args": {"pergunta": objetivo}, "motivo": "fallback (plano vazio)"}]

    return validos


def _executar_passo(passo: dict, contexto_anterior: str = "", tentativas: int = 2) -> dict:
    """
    Executa um passo com retry.
    Se for 'responder', injeta o contexto dos passos anteriores no prompt.
    """
    nome = passo["ferramenta"]
    args = passo.get("args", {}).copy()

    if nome not in FERRAMENTAS_DISPONIVEIS:
        return {"ok": False, "resultado": None, "erro": f"ferramenta desconhecida: {nome}"}

    # Se for 'responder', passa o contexto dos passos anteriores
    if nome == "responder" and contexto_anterior:
        pergunta_original = args.get("pergunta", "")
        args["pergunta"] = (
            f"OBJETIVO: {pergunta_original}\n\n"
            f"RESULTADOS OBTIDOS NOS PASSOS ANTERIORES:\n{contexto_anterior}\n\n"
            f"Com base APENAS nesses resultados, responda o objetivo em portugues. "
            f"Se os resultados nao tiverem a informacao, diga que nao conseguiu."
        )

    fn = FERRAMENTAS_DISPONIVEIS[nome]
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            print(f"[TASK] executando {nome}({list(args.keys())}) tentativa {tentativa}")
            resultado = fn(**args)

            if isinstance(resultado, dict) and resultado.get("status") == "erro":
                ultimo_erro = resultado.get("result", "erro desconhecido")
                print(f"[TASK] {nome} retornou erro: {str(ultimo_erro)[:120]}")
                time.sleep(1)
                continue

            return {"ok": True, "resultado": resultado, "erro": None}

        except Exception as e:
            ultimo_erro = f"{type(e).__name__}: {e}"
            print(f"[TASK] {nome} exception: {ultimo_erro}")
            time.sleep(1)

    return {"ok": False, "resultado": None, "erro": ultimo_erro}


def executar_task(objetivo: str, max_passos: int = 5) -> dict:
    """Executa uma task simples: planeja -> executa -> sintetiza."""
    print(f"[TASK] iniciando: {objetivo}")

    if not FERRAMENTAS_DISPONIVEIS:
        return {
            "status": "erro",
            "objetivo": objetivo,
            "plano": [],
            "historico": [],
            "resultado_final": None,
            "erro": "Nenhuma ferramenta registrada.",
        }

    # 1. PLANEJAR
    try:
        plano = _planejar(objetivo)
    except Exception as e:
        return {
            "status": "erro",
            "objetivo": objetivo,
            "plano": [],
            "historico": [],
            "resultado_final": None,
            "erro": f"Falha ao planejar: {type(e).__name__}: {e}",
        }

    print(f"[TASK] plano: {[p['ferramenta'] for p in plano]}")

    # 2. EXECUTAR (acumulando contexto)
    historico = []
    contexto_acumulado = ""

    for i, passo in enumerate(plano[:max_passos], 1):
        print(f"[TASK] passo {i}/{len(plano)}: {passo['ferramenta']}")

        # Passa o contexto acumulado pro responder
        r = _executar_passo(passo, contexto_anterior=contexto_acumulado)

        historico.append({
            "passo": i,
            "ferramenta": passo["ferramenta"],
            "args": passo.get("args", {}),
            "motivo": passo.get("motivo", ""),
            "ok": r["ok"],
            "resultado": r["resultado"],
            "erro": r["erro"],
        })

        # Acumula o resultado pro proximo passo
        if r["ok"] and passo["ferramenta"] != "responder":
            resultado_str = ""
            if isinstance(r["resultado"], dict):
                resultado_str = r["resultado"].get("result", "") or json.dumps(r["resultado"], ensure_ascii=False)
            else:
                resultado_str = str(r["resultado"])

            # Limita o tamanho pra nao estourar contexto
            if len(resultado_str) > 4000:
                resultado_str = resultado_str[:4000] + "\n...(truncado)"

            contexto_acumulado += f"\n--- {passo['ferramenta']} ---\n{resultado_str}\n"

        # Se um passo critico (nao-responder) falhou, para
        if not r["ok"] and passo["ferramenta"] != "responder":
            print(f"[TASK] passo {i} falhou definitivamente. Abortando.")
            return {
                "status": "erro",
                "objetivo": objetivo,
                "plano": plano,
                "historico": historico,
                "resultado_final": None,
                "erro": f"Passo {i} ({passo['ferramenta']}) falhou: {r['erro']}",
            }

    # 3. SINTETIZAR (se o responder nao foi chamado, chama agora com o contexto)
    for h in reversed(historico):
        if h["ferramenta"] == "responder" and h["ok"]:
            res = h["resultado"]
            if isinstance(res, dict):
                return {
                    "status": "ok",
                    "objetivo": objetivo,
                    "plano": plano,
                    "historico": historico,
                    "resultado_final": res.get("result"),
                    "erro": None,
                }

    # Se nao teve responder no plano, sintetiza agora
    prompt = (
        f"OBJETIVO: {objetivo}\n\n"
        f"RESULTADOS OBTIDOS:\n{contexto_acumulado[:5000]}\n\n"
        f"Responda o objetivo de forma clara e direta em portugues. "
        f"NAO invente informacoes que nao estao nos resultados."
    )

    try:
        resultado_final = _llm(
            prompt,
            "Voce responde de forma clara e objetiva em portugues. Nunca responda em outro idioma.",
        )
    except Exception as e:
        resultado_final = f"(falha ao sintetizar: {e})"

    return {
        "status": "ok",
        "objetivo": objetivo,
        "plano": plano,
        "historico": historico,
        "resultado_final": resultado_final,
        "erro": None,
    }