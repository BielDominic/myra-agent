"""
FASE 24.1 — Loop de autonomia adaptativo.
Cada iteracao: LLM decide 1 passo -> executa -> observa -> repete.
Integrado com o widget: notifica passo_atual, passo_num, historico.
"""
import json
import re
import time
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELO_PLANNER = "qwen2.5:7b"

FERRAMENTAS_DISPONIVEIS = {}
FERRAMENTAS_DESCRICOES = {}

MAX_PASSOS_PADRAO = 15
MAX_ERROS_CONSECUTIVOS = 3
MAX_REPETICOES_MESMA_ACAO = 2
TAMANHO_MAX_RESULTADO_HISTORICO = 800
TAMANHO_MAX_CONTEXTO_SINTESE = 6000


# Referencia global injetada pelo agent.py no startup
_widget_set_injetado = None


def _widget_notify(**kwargs):
    """Notifica o widget (usa a funcao injetada pelo agent.py)."""
    global _widget_set_injetado
    if _widget_set_injetado is None:
        return
    try:
        _widget_set_injetado(**kwargs)
    except Exception as e:
        print(f"[WIDGET-NOTIFY] erro: {e}")


def registrar_ferramenta(nome: str, fn, descricao: str = ""):
    FERRAMENTAS_DISPONIVEIS[nome] = fn
    if descricao:
        FERRAMENTAS_DESCRICOES[nome] = descricao


def _llm(prompt: str, system: str = "", timeout: int = 120) -> str:
    payload = {
        "model": MODELO_PLANNER,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 8192},
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


def _formatar_historico(historico: list) -> str:
    if not historico:
        return "(nenhum passo executado ainda)"
    linhas = []
    for h in historico:
        linhas.append(f"--- PASSO {h['passo']} ---")
        linhas.append(f"Ferramenta: {h['ferramenta']}")
        linhas.append(f"Args: {json.dumps(h['args'], ensure_ascii=False)}")
        if h["ok"]:
            res = h["resultado"]
            if isinstance(res, dict):
                res_str = res.get("result", json.dumps(res, ensure_ascii=False))
            else:
                res_str = str(res)
            if len(res_str) > TAMANHO_MAX_RESULTADO_HISTORICO:
                res_str = res_str[:TAMANHO_MAX_RESULTADO_HISTORICO] + "...(truncado)"
            linhas.append(f"Resultado: {res_str}")
        else:
            linhas.append(f"ERRO: {h['erro']}")
        linhas.append("")
    return "\n".join(linhas)


def _decidir_proximo_passo(objetivo: str, historico: list) -> dict:
    if FERRAMENTAS_DESCRICOES:
        ferramentas_str = "\n".join(
            f"- {nome}: {FERRAMENTAS_DESCRICOES.get(nome, 'sem descricao')}"
            for nome in sorted(FERRAMENTAS_DISPONIVEIS.keys())
        )
    else:
        ferramentas_str = ", ".join(sorted(FERRAMENTAS_DISPONIVEIS.keys()))

    historico_str = _formatar_historico(historico)

    system = (
        "Voce e um agente autonomo que decide UM passo por vez. "
        "Olhe o objetivo e o historico, e escolha a MELHOR proxima acao. "
        "Responda SEMPRE com JSON puro, sem texto antes ou depois."
    )

    prompt = f"""OBJETIVO: {objetivo}

HISTORICO DE PASSOS JA EXECUTADOS:
{historico_str}

FERRAMENTAS DISPONIVEIS:
{ferramentas_str}

REGRAS:
- Escolha UMA ferramenta por vez, ou finalize se o objetivo ja foi atingido.
- Escolha a ferramenta MAIS ESPECIFICA pro proximo passo.
- Se o historico ja tem a informacao necessaria, FINALIZE.
- Se algo deu errado no historico, tente outra abordagem.
- NAO repita a mesma acao com os mesmos args se ela ja falhou.
- Se um passo devolveu links/URLs, o proximo passo pode ser open_url ou read_page.
- Se um passo devolveu texto de uma pagina, o proximo pode ser extrair info ou finalizar.

FORMATO DA RESPOSTA (JSON puro):

Para chamar ferramenta:
{{
  "acao": "chamar",
  "ferramenta": "nome_da_ferramenta",
  "args": {{"chave": "valor"}},
  "motivo": "por que esse passo"
}}

Para finalizar:
{{
  "acao": "finalizar",
  "motivo": "por que considerar concluido"
}}
"""

    texto = _llm(prompt, system)
    data = _extrair_json(texto)

    if not data or "acao" not in data:
        print(f"[TASK] LLM nao retornou JSON valido. Texto cru: {texto[:200]}")
        return {"acao": "finalizar", "motivo": "erro ao decidir proximo passo"}

    return data


def _executar_passo(ferramenta: str, args: dict, tentativas: int = 2) -> dict:
    if ferramenta not in FERRAMENTAS_DISPONIVEIS:
        return {"ok": False, "resultado": None, "erro": f"ferramenta desconhecida: {ferramenta}"}

    fn = FERRAMENTAS_DISPONIVEIS[ferramenta]
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            print(f"[TASK] executando {ferramenta}({list(args.keys())}) tentativa {tentativa}")
            resultado = fn(**args)

            if isinstance(resultado, dict) and resultado.get("status") == "erro":
                ultimo_erro = resultado.get("result", "erro desconhecido")
                print(f"[TASK] {ferramenta} retornou erro: {str(ultimo_erro)[:120]}")
                time.sleep(1)
                continue

            return {"ok": True, "resultado": resultado, "erro": None}

        except Exception as e:
            ultimo_erro = f"{type(e).__name__}: {e}"
            print(f"[TASK] {ferramenta} exception: {ultimo_erro}")
            time.sleep(1)

    return {"ok": False, "resultado": None, "erro": ultimo_erro}


def _sintetizar(objetivo: str, historico: list) -> str:
    if not historico:
        return "(nenhum passo executado)"
    contexto = _formatar_historico(historico)
    prompt = (
        f"OBJETIVO: {objetivo}\n\n"
        f"HISTORICO DE EXECUCAO:\n{contexto[:TAMANHO_MAX_CONTEXTO_SINTESE]}\n\n"
        f"Com base APENAS nos resultados acima, responda o objetivo em portugues, "
        f"de forma clara e direta. Se os resultados nao tiverem a informacao, "
        f"diga exatamente o que conseguiu e o que nao conseguiu."
    )
    try:
        return _llm(
            prompt,
            "Voce responde de forma clara e objetiva em portugues. Nunca responda em outro idioma.",
        )
    except Exception as e:
        return f"(falha ao sintetizar: {e})"


def executar_task(objetivo: str, max_passos: int = MAX_PASSOS_PADRAO) -> dict:
    print(f"[TASK] iniciando (adaptativo): {objetivo}")

    if not FERRAMENTAS_DISPONIVEIS:
        return {
            "status": "erro",
            "objetivo": objetivo,
            "plano": [],
            "historico": [],
            "resultado_final": None,
            "erro": "Nenhuma ferramenta registrada.",
        }

    historico = []
    erros_consecutivos = 0
    acoes_repetidas = {}

            # Notifica o widget: passo_total (e garante state=running)
    _widget_notify(passo_total=max_passos, state="running")
    # Pequeno delay pra o widget pegar o estado running
    time.sleep(0.5)

    for passo_num in range(1, max_passos + 1):
        print(f"\n[TASK] === PASSO {passo_num}/{max_passos} ===")

        # Notifica o widget: novo passo
        _widget_notify(
            passo_num=passo_num,
            historico=[{"ferramenta": h["ferramenta"]} for h in historico],
        )
        # Delay pra o widget pegar o passo
        time.sleep(0.3)

        try:
            decisao = _decidir_proximo_passo(objetivo, historico)
        except Exception as e:
            print(f"[TASK] Erro ao decidir: {e}")
            break

        acao = decisao.get("acao", "")

        # Compatibilidade com chamadas de ferramenta emitidas diretamente pelo LLM
        # (ex.: {"acao":"browser_read_active_tab","args":[]}), além do formato
        # canônico {"acao":"chamar","ferramenta":"...","args":{...}}.
        if acao in FERRAMENTAS_DISPONIVEIS:
            decisao = {
                **decisao,
                "ferramenta": acao,
                "acao": "chamar",
            }
            acao = "chamar"

        if acao == "finalizar":
            print(f"[TASK] LLM decidiu finalizar: {decisao.get('motivo', '')}")
            break

        if acao == "chamar":
            ferramenta = decisao.get("ferramenta", "")
            args = decisao.get("args", {}) or {}
            motivo = decisao.get("motivo", "")

            # Alguns modelos retornam argumentos posicionais como lista. Converte
            # para kwargs usando a assinatura registrada da ferramenta.
            if isinstance(args, list):
                import inspect
                parametros = [
                    p for p in inspect.signature(FERRAMENTAS_DISPONIVEIS[ferramenta]).parameters.values()
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    and p.default is inspect.Parameter.empty
                ] if ferramenta in FERRAMENTAS_DISPONIVEIS else []
                args = {p.name: valor for p, valor in zip(parametros, args)}
            elif not isinstance(args, dict):
                args = {}

            if ferramenta not in FERRAMENTAS_DISPONIVEIS:
                print(f"[TASK] ferramenta invalida: {ferramenta}")
                erros_consecutivos += 1
                historico.append({
                    "passo": passo_num,
                    "ferramenta": ferramenta,
                    "args": args,
                    "motivo": motivo,
                    "ok": False,
                    "resultado": None,
                    "erro": f"ferramenta desconhecida: {ferramenta}",
                })
                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    print("[TASK] muitos erros consecutivos. Abortando.")
                    break
                continue

            chave = f"{ferramenta}:{json.dumps(args, sort_keys=True)}"
            acoes_repetidas[chave] = acoes_repetidas.get(chave, 0) + 1
            if acoes_repetidas[chave] > MAX_REPETICOES_MESMA_ACAO:
                print(f"[TASK] Acao repetida {acoes_repetidas[chave]}x. Abortando.")
                break

            # Notifica o widget: qual ferramenta ta rodando AGORA
            _widget_notify(passo_atual=ferramenta, state="running")
            # Delay pra o widget pegar o passo_atual
            time.sleep(0.3)

            r = _executar_passo(ferramenta, args)

            historico.append({
                "passo": passo_num,
                "ferramenta": ferramenta,
                "args": args,
                "motivo": motivo,
                "ok": r["ok"],
                "resultado": r["resultado"],
                "erro": r["erro"],
            })

            # Notifica o widget: historico atualizado
            _widget_notify(
                historico=[{"ferramenta": h["ferramenta"]} for h in historico],
                state="running",
            )

            if r["ok"]:
                erros_consecutivos = 0
            else:
                erros_consecutivos += 1
                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    print("[TASK] muitos erros consecutivos. Abortando.")
                    break

            continue

        print(f"[TASK] acao desconhecida: {acao}")
        break

    print(f"\n[TASK] finalizando com {len(historico)} passos executados")
    resultado_final = _sintetizar(objetivo, historico)

    return {
        "status": "ok",
        "objetivo": objetivo,
        "plano": [{"ferramenta": h["ferramenta"], "args": h["args"]} for h in historico],
        "historico": historico,
        "resultado_final": resultado_final,
        "erro": None,
    }