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
MAX_REPETICOES_MESMA_ACAO = 1
TAMANHO_MAX_RESULTADO_HISTORICO = 5000
TAMANHO_MAX_CONTEXTO_SINTESE = 12000


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


def _formatar_resultado(res: dict) -> str:
    """Formata resultados do navegador priorizando texto e tabelas estruturadas."""
    partes = []
    if res.get("title"):
        partes.append(f"Title: {res['title']}")
    if res.get("url"):
        partes.append(f"URL: {res['url']}")
    if res.get("text"):
        partes.append(f"\nTexto visivel:\n{str(res['text'])[:2500]}")
    if res.get("tables"):
        partes.append("\n=== TABELAS ===")
        for i, tabela in enumerate(res["tables"][:3], 1):
            caption = tabela.get("caption") or f"tabela {i}"
            partes.append(f"\n--- {caption} ---")
            for row in tabela.get("rows", [])[:30]:
                celulas = [str(c).strip() for c in row if c is not None]
                if len(celulas) == 2:
                    partes.append(f"{celulas[0]}: {celulas[1]}")
                elif celulas:
                    partes.append(" | ".join(celulas))
    if res.get("links"):
        partes.append("\n=== LINKS ===")
        for link in res["links"][:10]:
            partes.append(f"{link.get('text', '')}: {link.get('href', '')}")
    if res.get("buttons"):
        partes.append(f"\nBotoes: {', '.join(str(b) for b in res['buttons'][:15])}")
    if res.get("inputs"):
        partes.append(f"\nCampos: {len(res['inputs'])} inputs")
    return "\n".join(partes)


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
                if "tables" in res or "text" in res:
                    res_str = _formatar_resultado(res)
                else:
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
    # Em pedidos de navegação, priorize operar no navegador visível do usuário.
    # Mantemos as ferramentas de pesquisa disponíveis para outros tipos de objetivo.
    objetivo_lower = objetivo.lower()
    termos_navegacao = ("abre", "abrir", "navega", "visita", "acesse", "acessa", "vai para", "entre no site", "entre em", "no navegador")
    eh_navegacao = any(t in objetivo_lower for t in termos_navegacao)
    ferramentas_ocultas_navegacao = {
        "web_search_structured", "youtube_search", "youtube_summarize",
        "youtube_ask", "youtube_transcript", "youtube_channel_latest",
        "search_google", "search_google_structured",
    }
    nomes_prompt = sorted(
        nome for nome in FERRAMENTAS_DISPONIVEIS
        if not (eh_navegacao and nome in ferramentas_ocultas_navegacao)
    )
    if FERRAMENTAS_DESCRICOES:
        ferramentas_str = "\n".join(
            f"- {nome}: {FERRAMENTAS_DESCRICOES.get(nome, 'sem descricao')}"
            for nome in nomes_prompt
        )
    else:
        ferramentas_str = ", ".join(nomes_prompt)

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
- Se algo deu errado no historico, MUDE DE ESTRATEGIA; nao repita a mesma ferramenta com os mesmos argumentos.
- Se uma ferramenta falhou 2 vezes, use uma ferramenta DIFERENTE ou finalize explicando o bloqueio.
- NUNCA chame a mesma ferramenta com os mesmos argumentos mais de uma vez.
- Se o objetivo pede abrir um site E pesquisar, sao duas acoes diferentes.
- FINALIZE somente quando o objetivo estiver COMPLETAMENTE atendido.
- Para "pesquisar X no Google", use open_url com "https://www.google.com/search?q=..." e codifique o termo na URL; nao use ferramenta de pesquisa por API.
- Se "YouTube" for o site a abrir, use open_url com "https://www.youtube.com/results?search_query=...".
- Use youtube_search apenas quando o objetivo pedir explicitamente metadados/resultados de videos.
- Se o usuario perguntar quais abas estao abertas, use browser_get_tabs.
- Se o usuario pedir para abrir um site em uma nova aba, use browser_new_tab com a URL HTTP/HTTPS completa; nao substitua a aba atual.
- Se o usuario pedir para preencher ou digitar em um campo de uma pagina aberta, use browser_type_text com campo (seletor CSS ou label exato) e texto; se o campo nao estiver claro, leia a pagina primeiro e nao adivinhe.
- Se o usuario quiser ler uma aba especifica e voce nao sabe qual, use browser_get_tabs primeiro.
- Se o usuario mencionar um site, dominio ou trecho de URL para ler, prefira browser_read_active_tab com o argumento url_contains correspondente; isso seleciona a aba certa mesmo com varias abas abertas.
- Para "leia o que esta aberto no meu Chrome" sem indicar site, use browser_read_active_tab sem url_contains; o bridge escolhe a aba ativa ou a pagina web mais recente quando o Open WebUI esta ativo.
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
        return "Nao foi executada nenhuma ferramenta. Verifique a decisao do planner e tente reformular o objetivo."
    contexto = _formatar_historico(historico)
    prompt = (
        f"OBJETIVO: {objetivo}\n\n"
        f"HISTORICO DE EXECUCAO:\n{contexto[:TAMANHO_MAX_CONTEXTO_SINTESE]}\n\n"
        f"Com base APENAS nos resultados acima, responda o objetivo em portugues, "
        f"de forma clara e direta. Se os resultados nao tiverem a informacao, "
        f"diga exatamente o que conseguiu e o que nao conseguiu. "
        f"Se a tarefa pede um dado especifico (populacao, preco, data ou numero), "
        f"procure tambem nas TABELAS listadas no historico, nao apenas no texto corrido. "
        f"Dados estruturados costumam estar em tabelas ou listas."
    )
    try:
        return _llm(
            prompt,
            "Voce responde de forma clara e objetiva em portugues. Nunca responda em outro idioma.",
        )
    except Exception as e:
        # Fallback deterministico: preserva os resultados obtidos mesmo se o LLM falhar.
        partes = []
        for h in historico:
            ferramenta = h.get("ferramenta", "ferramenta")
            if h.get("ok"):
                resultado = h.get("resultado")
                if isinstance(resultado, dict):
                    resultado = resultado.get("result", json.dumps(resultado, ensure_ascii=False))
                if resultado not in (None, ""):
                    partes.append(f"{ferramenta}: {str(resultado)[:1200]}")
            else:
                partes.append(f"{ferramenta}: falhou — {h.get('erro') or 'erro sem detalhes'}")
        if partes:
            return "Nao consegui gerar uma sintese pelo modelo. Resultados obtidos:\n" + "\n".join(partes)
        return f"Nao foi possivel concluir a tarefa nem gerar uma sintese ({type(e).__name__}: {e})."


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

    for passo_num in range(1, max_passos + 1):
        print(f"\n[TASK] === PASSO {passo_num}/{max_passos} ===")

        # Notifica o widget: novo passo
        _widget_notify(
            passo_num=passo_num,
            historico=[{"ferramenta": h["ferramenta"]} for h in historico],
        )

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