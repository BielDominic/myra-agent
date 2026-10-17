"""
FASE 24.1 — Loop de autonomia adaptativo.
FASE 26 — Ciclo autonomo: decide 1 passo -> executa -> observa -> verifica ->
recupera -> persiste. Permite pausar/retomar e sobrevive a reinicio.

Cada iteracao: LLM decide 1 passo -> executa -> observa -> verifica -> repete.
Integrado com o widget: notifica passo_atual, passo_num, historico.
"""
import json
from tasks.cancel_state import esta_cancelada, esta_pausada, resetar, resetar_pausa
from tasks import autonomy, task_store
import re
import time
import unicodedata
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELO_PLANNER = "qwen2.5:3b-instruct-q5_K_M"

FERRAMENTAS_DISPONIVEIS = {}
FERRAMENTAS_DESCRICOES = {}

MAX_PASSOS_PADRAO = 15
# O limite de erros consecutivos e maior que o de recuperacoes para que o
# motivo explicito da recuperacao (com o ultimo erro) seja sempre o que
# encerra a task, em vez de um contador generico.
MAX_ERROS_CONSECUTIVOS = autonomy.LIMITE_RECUPERACOES + 1
MAX_REPETICOES_MESMA_ACAO = 1
TAMANHO_MAX_RESULTADO_HISTORICO = 5000
TAMANHO_MAX_CONTEXTO_SINTESE = 12000
MAX_FINALIZACOES_RECUSADAS = 2      # vezes que recusamos "finalizar" sem evidencia
MAX_RECUPERACOES = autonomy.LIMITE_RECUPERACOES
PASSOS_EXTRA_AO_RETOMAR = 5         # folga de passos ao retomar uma task pausada


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


_COMPUTER_ACTIVITY_PREFIXES = ("browser_", "pc_", "vision_", "computer_", "mouse_", "keyboard_", "desktop_")
_COMPUTER_ACTIVITY_TOOLS = {
    "open_url", "read_page", "click_element", "type_text",
    "search_google", "search_google_visivel", "press_key",
}


def _is_computer_activity_tool(name: str) -> bool:
    """True somente para ferramentas que interagem com navegador/desktop."""
    tool = str(name or "").strip().lower()
    return tool in _COMPUTER_ACTIVITY_TOOLS or tool.startswith(_COMPUTER_ACTIVITY_PREFIXES)

# Ferramentas legadas que deixam de ser expostas ao planner quando
# a ferramenta equivalente do Browser Bridge estiver registrada.
# Isso altera somente o registro usado pelo planner; as rotas HTTP do agent.py
# permanecem intactas para clientes legados, incluindo o Open WebUI.
_FERRAMENTAS_LEGADAS_COM_BRIDGE = {
    "open_url": {"browser_new_tab", "browser_navigate_active_tab"},
    "read_page": {"browser_read_page", "browser_read_active_tab"},
    "click_element": {"browser_click_text"},
    "type_text": {"browser_type_text"},
    "search_google": {"browser_search_google", "browser_search_google_visivel"},
    "wait": {"browser_wait"},
}


def registrar_ferramenta(nome: str, fn, descricao: str = ""):
    # Se o Bridge já foi registrado antes de uma ferramenta legada, não a
    # reinsira no registro do planner.
    equivalentes = _FERRAMENTAS_LEGADAS_COM_BRIDGE.get(nome)
    if equivalentes and any(eq in FERRAMENTAS_DISPONIVEIS for eq in equivalentes):
        FERRAMENTAS_DISPONIVEIS.pop(nome, None)
        FERRAMENTAS_DESCRICOES.pop(nome, None)
        return

    FERRAMENTAS_DISPONIVEIS[nome] = fn
    if descricao:
        FERRAMENTAS_DESCRICOES[nome] = descricao

    # Quando uma ferramenta Bridge é registrada, retire apenas seu alias
    # legado do planner. Rotas HTTP não dependem deste dicionário.
    for legado, nomes_bridge in _FERRAMENTAS_LEGADAS_COM_BRIDGE.items():
        if nome in nomes_bridge:
            FERRAMENTAS_DISPONIVEIS.pop(legado, None)
            FERRAMENTAS_DESCRICOES.pop(legado, None)


def _llm(prompt: str, system: str = "", timeout: int = 120, format_json: bool = True) -> str:
    payload = {
        "model": MODELO_PLANNER,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }
    if format_json:
        payload["format"] = "json"
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


def _eh_pedido_hora_atual(objetivo: str) -> bool:
    """Reconhece pedidos curtos e explicitos pela hora/data atual em portugues."""
    texto = unicodedata.normalize("NFKD", str(objetivo or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto).strip()
    padroes = (
        "que horas sao",
        "que hora e",
        "qual a hora",
        "qual e a hora",
        "hora atual",
        "horario atual",
        "horas agora",
        "hora agora",
        "que dia e hoje",
        "data de hoje",
        "data e hora atual",
    )
    return any(padrao in texto for padrao in padroes)


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




def _adicionar_observacao_ao_historico_str(historico: list) -> str:
    """Versao melhorada de _formatar_historico que inclui observacao,
    verificacao do objetivo e recuperacoes tentadas (FASE 26)."""
    base = _formatar_historico(historico)
    extras = []
    for h in historico:
        obs = h.get("observacao")
        if obs and obs.get("status") == "ok":
            extras.append(
                f"  - Passo {h.get('passo')}: obs -> sucesso={obs.get('sucesso')} "
                f"objetivo_atingido={obs.get('objetivo_atingido')} "
                f"motivo={str(obs.get('motivo', ''))[:150]}"
            )
        ver = h.get("verificacao")
        if ver:
            extras.append(
                f"  - Passo {h.get('passo')}: verificacao -> atingido={ver.get('atingido')} "
                f"confianca={ver.get('confianca')} motivo={str(ver.get('motivo', ''))[:150]}"
            )
        rec = h.get("recuperacao")
        if rec:
            extras.append(
                f"  - Passo {h.get('passo')}: recuperacao -> recuperar={rec.get('recuperar')} "
                f"desistir={rec.get('desistir')} motivo={str(rec.get('motivo', ''))[:150]}"
            )
    if extras:
        base += "\n\nOBSERVACOES / VERIFICACOES:\n" + "\n".join(extras)
    return base

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


def _decidir_proximo_passo(
    objetivo: str,
    historico: list,
    diretriz_recuperacao: str = "",
    acoes_bloqueadas: list | None = None,
) -> dict:
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
    # Se o objetivo e sobre ARQUIVO/local, esconde TODAS as ferramentas de browser.
    # Sem isto, o 3b chama browser_new_tab pra "pesquisar como criar arquivo".
    termos_arquivo = (
        "escreve", "escrever", "salvar arquivo", "criar arquivo", "criar pasta",
        "arquivo", "pasta", "diretorio", "ler arquivo", "apagar arquivo",
        "deletar arquivo", "mover arquivo", "renomear arquivo", "listar arquivos",
        "criar diretorio", "apagar pasta",
    )
    eh_arquivo = any(t in objetivo_lower for t in termos_arquivo)
    ferramentas_ocultas_arquivo = {
        "browser_new_tab", "browser_search_google", "browser_search_google_visivel",
        "browser_navigate_active_tab", "browser_read_active_tab", "browser_read_page",
        "browser_scroll", "browser_click_text", "browser_close_tab",
        "browser_get_tabs", "browser_type_text", "browser_wait",
        "web_search_structured", "search_google_structured", "search_google",
    }
    nomes_prompt = sorted(
        nome for nome in FERRAMENTAS_DISPONIVEIS
        if not (eh_navegacao and nome in ferramentas_ocultas_navegacao)
        and not (eh_arquivo and nome in ferramentas_ocultas_arquivo)
    )
    if FERRAMENTAS_DESCRICOES:
        ferramentas_str = "\n".join(
            f"- {nome}: {FERRAMENTAS_DESCRICOES.get(nome, 'sem descricao')}"
            for nome in nomes_prompt
        )
    else:
        ferramentas_str = ", ".join(nomes_prompt)

    historico_str = _adicionar_observacao_ao_historico_str(historico)

    system = (
        "Voce e um agente autonomo que decide UM passo por vez. "
        "Olhe o objetivo e o historico, e escolha a MELHOR proxima acao. "
        "Responda SEMPRE com JSON puro, sem texto antes ou depois."
    )

    # FASE 26 - bloco de recuperacao: diz explicitamente o que nao repetir.
    bloco_recuperacao = ""
    if diretriz_recuperacao:
        bloco_recuperacao = f"\nDIRETRIZ DE RECUPERACAO (obrigatoria para o proximo passo):\n{diretriz_recuperacao}\n"
    if acoes_bloqueadas:
        lista = "\n".join(f"- {assinatura}" for assinatura in acoes_bloqueadas)
        bloco_recuperacao += f"\nACOES BLOQUEADAS (nao repita nenhuma):\n{lista}\n"

    prompt = f"""OBJETIVO: {objetivo}

HISTORICO DE PASSOS JA EXECUTADOS:
{historico_str}
{bloco_recuperacao}
FERRAMENTAS DISPONIVEIS:
{ferramentas_str}

REGRA CRITICA ANTI-ALUCINACAO (LEIA ANTES DE TUDO):

- Voce NUNCA executou nada ainda. O historico mostra apenas passos JA executados.
- Se o historico esta VAZIO, voce NAO chamou nenhuma ferramenta ainda.
- NUNCA finalize dizendo que uma ferramenta retornou algo se voce NAO chamou ela neste passo.
- Se o objetivo pede hora, VOCE DEVE CHAMAR get_current_time AGORA. Nao diga que ja chamou.
- Exemplo ERRADO: acao=finalizar, motivo='get_current_time retornou a hora'
- Exemplo CERTO:  acao=chamar, ferramenta=get_current_time, motivo='obter hora'

REGRAS DE TEMA (LEIA PRIMEIRO - PRIORIDADE MAXIMA):

Se o objetivo menciona HORA, DATA, DIA, MES ou ANO:
  -> use get_current_time().
  Exemplos: "que horas sao", "que dia e hoje", "qual a data".

Se o objetivo menciona CLIMA, TEMPO, TEMPERATURA, CHUVA, FRIO ou CALOR:
  -> use get_weather(cidade="...").
  Exemplos: "clima em Dublin", "vai chover hoje", "esta frio?".

Se o objetivo menciona CRIAR, ESCREVER ou SALVAR arquivo:
  -> use write_file(caminho, conteudo).
  Exemplos: "escreve um arquivo texto.txt com ola".

Se o objetivo menciona LER ou MOSTRAR arquivo:
  -> use read_file(caminho) ou list_dir.

Se o objetivo menciona LISTAR arquivos de uma pasta:
  -> use list_dir(caminho).

Se o objetivo menciona APAGAR ou DELETAR arquivo:
  -> use delete_file(caminho).

Se o objetivo menciona EXECUTAR ou RODAR codigo Python:
  -> use code_run(codigo) ou run_python(codigo).

Se o objetivo menciona NOTAS, ANOTACOES, SALVAR ANOTACAO:
  -> use save_note(texto) ou read_notes().

Se o objetivo menciona EMAIL, GMAIL, CAIXA DE ENTRADA:
  -> use email_list/email_read/email_send/email_search.

Se o objetivo menciona ABRIR SITE, NAVEGAR, PESQUISAR NO GOOGLE:
  -> use browser_new_tab(url) ou browser_search_google(termo).

Se o objetivo menciona CLICAR, DIGITAR, VISUALMENTE em elemento da tela:
  -> use vision_click(descricao) ou vision_type(descricao, texto).

Se o objetivo menciona ROLAR a pagina:
  -> use browser_scroll(direcao, quantidade).

Se o objetivo menciona FECHAR aba do navegador:
  -> use browser_close_tab(tab_id).

REGRA CRITICA: se o tema NAO envolve navegador, NAO use browser_*.
Se o tema NAO envolve arquivo, NAO use write_file/read_file.

OUTRAS REGRAS:

- Escolha UMA ferramenta por vez, ou finalize se o objetivo ja foi atingido.
- Escolha a ferramenta MAIS ESPECIFICA pro proximo passo.
- REGRA CRITICA: se uma ferramenta de LEITURA SIMPLES (get_current_time,
  get_weather, read_notes, email_list, list_dir) retornou com sucesso,
  o objetivo JA FOI ATINGIDO. FINALIZE com o resultado. NAO chame de novo.
- Se o historico ja tem a informacao necessaria, FINALIZE.
- Se algo deu errado no historico, MUDE DE ESTRATEGIA; nao repita a mesma ferramenta com os mesmos argumentos.
- Se uma ferramenta falhou 2 vezes, use uma ferramenta DIFERENTE ou finalize explicando o bloqueio.
- NUNCA chame a mesma ferramenta com os mesmos argumentos mais de uma vez.
- FINALIZE somente quando o objetivo estiver COMPLETAMENTE atendido.
- So finalize com EVIDENCIA observavel nos resultados; se as OBSERVACOES/VERIFICACOES mostrarem falha, tente outra estrategia antes de finalizar.
- Se houver DIRETRIZ DE RECUPERACAO, siga-a e nunca repita uma ACAO BLOQUEADA.
- Se o observer indicar "objetivo_atingido: true" e "sucesso: true", pode finalizar.
- Se o usuario pedir para preencher ou digitar em campo de pagina aberta, use browser_type_text com campo e texto; leia a pagina primeiro se nao estiver claro.
- Se o usuario mencionar site, dominio ou trecho de URL, use browser_read_active_tab com url_contains correspondente.
- Para "leia o que esta aberto no Chrome" sem indicar site, use browser_read_active_tab sem url_contains.
- Se um passo devolveu links/URLs, use browser_new_tab para abrir ou browser_read_page para ler.
- DIFERENCA CRITICA: read_page_structured le o DOM/HTML. vision_locate/vision_click/vision_type olham os PIXELS. Use vision_* para CLICAR em algo visual.


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

    # Guarda de confiabilidade: pedidos diretos pela hora atual nao podem ser
    # encerrados sem executar a ferramenta que fornece o horario real.
    # O modelo continua sendo consultado normalmente; isto so corrige uma
    # decisao prematura/invalida antes do primeiro passo.
    if (
        not historico
        and "get_current_time" in FERRAMENTAS_DISPONIVEIS
        and _eh_pedido_hora_atual(objetivo)
        and (not isinstance(data, dict) or data.get("acao") != "chamar"
             or data.get("ferramenta") != "get_current_time")
    ):
        print("[TASK] fallback de intencao: pedido de hora -> get_current_time")
        return {
            "acao": "chamar",
            "ferramenta": "get_current_time",
            "args": {},
            "motivo": "pedido explicito pela hora atual; consultar a ferramenta de horario real",
        }

    if not data or "acao" not in data:
        print(f"[TASK] LLM nao retornou JSON valido. Texto cru: {texto[:200]}")
        return {"acao": "finalizar", "motivo": "erro ao decidir proximo passo"}

    return data


# ============================================================
# OBSERVER - avalia se a acao anterior atingiu o objetivo
# ============================================================

FERRAMENTAS_OBSERVAVEIS = {
    # Visao / desktop
    "vision_click", "vision_type", "vision_locate",
    "pc_click", "pc_double_click", "pc_right_click",
    "pc_type_text", "pc_hotkey", "pc_press_key",
    # Browser
    "browser_click_text", "browser_type_text",
    "browser_navigate_active_tab", "browser_new_tab",
    "browser_search_google", "browser_search_google_visivel",
    # Email
    "email_send", "email_reply", "email_delete_by_search",
    "email_mark_read", "email_mark_unread", "email_move",
    # Arquivos
    "write_file", "delete_file", "move_file", "create_dir",
    # Codigo
    "code_run", "run_python",
}


def _deve_observar(ferramenta: str) -> bool:
    """Retorna True se a ferramenta muda estado (vale observar)."""
    return ferramenta in FERRAMENTAS_OBSERVAVEIS


def _observar(objetivo: str, ferramenta: str, args: dict, resultado, erro) -> dict | None:
    """Chama o observer. Retorna None se der erro ou nao precisar observar."""
    if not _deve_observar(ferramenta):
        return None
    try:
        from computer.observer import observar
        obs = observar(objetivo, {
            "ferramenta": ferramenta,
            "args": args,
            "resultado": resultado,
            "erro": erro,
        })
        if obs.get("status") == "ok":
            return obs
    except Exception as e:
        print(f"[OBSERVER] erro: {e}")
    return None


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
            format_json=False,
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


def _resposta(status: str, objetivo: str, historico: list, task_id: str | None = None, **extra) -> dict:
    """Monta a resposta padrao de uma task (mesmo formato de antes + task_id)."""
    dados = {
        "status": status,
        "objetivo": objetivo,
        "task_id": task_id,
        "plano": [{"ferramenta": h.get("ferramenta"), "args": h.get("args")} for h in historico],
        "historico": historico,
        "resultado_final": None,
        "erro": None,
    }
    dados.update(extra)
    return dados


def _persistir(task_id: str | None, **kwargs) -> None:
    """Salva o estado da task no SQLite. Nunca derruba a execucao da task."""
    if not task_id:
        return
    try:
        task_store.salvar_task(task_id, **kwargs)
    except Exception as e:
        print(f"[STORE] erro ao salvar task {task_id}: {e}")


def _evento(task_id: str | None, tipo: str, detalhe: str = "", passo: int | None = None) -> None:
    if not task_id:
        return
    try:
        task_store.registrar_evento(task_id, tipo, detalhe=detalhe, passo=passo)
    except Exception as e:
        print(f"[STORE] erro ao registrar evento: {e}")


def _bloquear_acao(acoes_bloqueadas: list, assinaturas: list) -> None:
    for assinatura in assinaturas or []:
        if assinatura not in acoes_bloqueadas:
            acoes_bloqueadas.append(assinatura)


def executar_task(
    objetivo: str,
    max_passos: int = MAX_PASSOS_PADRAO,
    task_id: str | None = None,
    historico: list | None = None,
    passo_inicial: int = 1,
    persistir: bool = True,
) -> dict:
    """Loop adaptativo completo: decide -> executa -> observa -> verifica ->
    recupera -> persiste.

    Args:
        objetivo: objetivo da task.
        max_passos: limite de passos desta execucao.
        task_id: id de uma task existente (retomada). Se None, cria uma nova.
        historico: historico ja executado (usado ao retomar).
        passo_inicial: numero do proximo passo ao retomar.
        persistir: desliga a persistencia (usado em testes/execucoes avulsas).
    """
    print(f"[TASK] iniciando (adaptativo): {objetivo}")

    if not FERRAMENTAS_DISPONIVEIS:
        return _resposta("erro", objetivo, [], task_id, erro="Nenhuma ferramenta registrada.")

    historico = list(historico or [])
    erros_consecutivos = 0
    acoes_repetidas = {}
    acoes_bloqueadas: list = []
    recuperacoes_usadas = 0
    finalizacoes_recusadas = 0
    diretriz_recuperacao = ""
    motivo_encerramento = ""
    erro_encerramento = ""

    # Reconstroi o estado do ciclo a partir do historico retomado: guarda
    # anti-repeticao, acoes bloqueadas pela recuperacao e recuperacoes usadas.
    # Sem isto, retomar uma task perderia o contexto de recuperacao (FASE 26).
    for h in historico:
        chave_antiga = autonomy.assinatura_acao(h.get("ferramenta", ""), h.get("args"))
        acoes_repetidas[chave_antiga] = acoes_repetidas.get(chave_antiga, 0) + 1
        rec = h.get("recuperacao")
        if isinstance(rec, dict):
            _bloquear_acao(acoes_bloqueadas, rec.get("acoes_bloqueadas"))
            if rec.get("recuperar"):
                recuperacoes_usadas += 1

    # Cria (ou reaproveita) o registo persistido da task.
    if persistir and not task_id:
        try:
            registo = task_store.criar_task(objetivo, max_passos=max_passos)
            task_id = registo["task_id"]
            _evento(task_id, "inicio", f"objetivo: {objetivo[:300]}")
        except Exception as e:
            print(f"[STORE] nao foi possivel persistir a task: {e}")
            task_id = None
    elif persistir and task_id:
        _persistir(task_id, estado=task_store.ESTADO_EM_EXECUCAO)

    # Publica o ID persistido no widget para que pausar/retomar use o registro certo.
    # O ID tempor?rio criado por /task_simple n?o ? o task_id do SQLite.
    _widget_notify(task_id=task_id, passo_total=max_passos, state="running", computer_activity=False)

    for passo_num in range(passo_inicial, max_passos + 1):
        # Checa cancelamento antes de cada passo
        if esta_cancelada():
            print("[TASK] cancelada pelo usuario - abortando")
            _widget_notify(state="idle")
            _persistir(task_id, estado=task_store.ESTADO_CANCELADO, terminado=True)
            _evento(task_id, "cancelada", "cancelada pelo usuario", passo=passo_num)
            return _resposta("cancelado", objetivo, historico, task_id)

        # FASE 26 - pausa: guarda o estado e devolve o controle sem perder contexto
        if esta_pausada():
            print("[TASK] pausada pelo usuario - estado persistido")
            _widget_notify(passo_atual="PAUSADO", state="running")
            _persistir(task_id, estado=task_store.ESTADO_PAUSADO, passo_atual=len(historico))
            _evento(task_id, "pausada", "pausa solicitada pelo usuario", passo=passo_num)
            return _resposta(
                "pausado", objetivo, historico, task_id,
                erro=None,
                passo_atual=len(historico),
            )

        print(f"\n[TASK] === PASSO {passo_num}/{max_passos} ===")

        # Notifica o widget: novo passo
        _widget_notify(
            passo_num=passo_num,
            historico=[{"ferramenta": h["ferramenta"]} for h in historico],
            computer_activity=False,
        )

        if esta_cancelada():
            print("[TASK] cancelada antes de decidir")
            _widget_notify(state="idle")
            _persistir(task_id, estado=task_store.ESTADO_CANCELADO, terminado=True)
            _evento(task_id, "cancelada", "cancelada antes de decidir", passo=passo_num)
            return _resposta("cancelado", objetivo, historico, task_id)

        try:
            decisao = _decidir_proximo_passo(
                objetivo,
                historico,
                diretriz_recuperacao=diretriz_recuperacao,
                acoes_bloqueadas=acoes_bloqueadas,
            )
        except Exception as e:
            print(f"[TASK] Erro ao decidir: {e}")
            motivo_encerramento = f"erro ao decidir o proximo passo: {type(e).__name__}: {e}"
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
            motivo_final = str(decisao.get("motivo", ""))[:200]
            verificacao = autonomy.verificar(objetivo, historico)
            if historico:
                historico[-1]["verificacao"] = verificacao

            # FASE 26 - nao aceita "finalizar" quando existe evidencia forte de falha.
            evidencia_de_falha = (
                verificacao.get("atingido") is False
                and verificacao.get("confianca") == "alta"
                and bool(historico)
            )
            if evidencia_de_falha and finalizacoes_recusadas < MAX_FINALIZACOES_RECUSADAS:
                finalizacoes_recusadas += 1
                ultimo = historico[-1]
                rec = autonomy.recuperar(
                    ultimo.get("ferramenta", ""),
                    ultimo.get("args", {}),
                    ultimo.get("erro") or verificacao.get("motivo"),
                    historico,
                    recuperacoes_usadas=recuperacoes_usadas,
                )
                recuperacoes_usadas += 1
                ultimo["recuperacao"] = rec
                _bloquear_acao(acoes_bloqueadas, rec.get("acoes_bloqueadas"))
                _persistir(task_id, historico=historico, passo_atual=len(historico))
                _evento(
                    task_id, "finalizacao_recusada",
                    f"{verificacao.get('motivo')} | {rec.get('motivo')}", passo=passo_num,
                )
                print(f"[VERIFICAR] finalizacao recusada: {verificacao.get('motivo')}")
                if rec.get("desistir"):
                    erro_encerramento = rec.get("motivo", "recuperacao esgotada")
                    break
                diretriz_recuperacao = rec.get("diretriz", "")
                continue

            if evidencia_de_falha:
                # O planner insiste em declarar sucesso, mas a evidencia observada
                # diz o contrario: encerra como falha em vez de mentir sucesso.
                erro_encerramento = (
                    "o planner declarou o objetivo concluido, mas a evidencia observada "
                    f"indica falha: {verificacao.get('motivo')}"
                )
                _evento(task_id, "sucesso_sem_evidencia", erro_encerramento, passo=passo_num)
                print(f"[VERIFICAR] encerrando sem sucesso: {erro_encerramento}")
                break

            print(f"[TASK] LLM decidiu finalizar: {motivo_final}")
            motivo_encerramento = motivo_final
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

            if esta_cancelada():
                print("[TASK] cancelada antes de executar ferramenta")
                _widget_notify(state="idle")
                _persistir(task_id, estado=task_store.ESTADO_CANCELADO, terminado=True)
                _evento(task_id, "cancelada", "cancelada antes de executar", passo=passo_num)
                return _resposta("cancelado", objetivo, historico, task_id)

            if esta_pausada():
                print("[TASK] pausada antes de executar ferramenta")
                _widget_notify(passo_atual="PAUSADO", state="running")
                _persistir(task_id, estado=task_store.ESTADO_PAUSADO, passo_atual=len(historico))
                _evento(task_id, "pausada", "pausa antes de executar", passo=passo_num)
                return _resposta("pausado", objetivo, historico, task_id, passo_atual=len(historico))

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
                    "timestamp": time.time(),
                })
                _persistir(task_id, historico=historico, passo_atual=passo_num)
                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    print("[TASK] muitos erros consecutivos. Abortando.")
                    erro_encerramento = f"{erros_consecutivos} erros consecutivos (ferramenta desconhecida)"
                    break
                continue

            chave = autonomy.assinatura_acao(ferramenta, args)
            acoes_repetidas[chave] = acoes_repetidas.get(chave, 0) + 1

            # FASE 26 - guarda de recuperacao: nunca reexecuta uma acao ja bloqueada
            # (verificado antes do guarda de repeticao para dar um motivo explicito).
            if chave in acoes_bloqueadas:
                print(f"[RECUPERAR] acao bloqueada recusada: {chave}")
                erros_consecutivos += 1
                historico.append({
                    "passo": passo_num,
                    "ferramenta": ferramenta,
                    "args": args,
                    "motivo": motivo,
                    "ok": False,
                    "resultado": None,
                    "erro": "acao bloqueada apos falhas repetidas (recuperacao)",
                    "timestamp": time.time(),
                })
                _evento(task_id, "acao_bloqueada", chave, passo=passo_num)
                _persistir(task_id, historico=historico, passo_atual=passo_num)
                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    erro_encerramento = (
                        f"o planner insistiu em acoes bloqueadas apos falhas; "
                        f"ultima acao recusada: {chave}"
                    )
                    break
                continue

            if acoes_repetidas[chave] > MAX_REPETICOES_MESMA_ACAO:
                print(f"[TASK] Acao repetida {acoes_repetidas[chave]}x. Abortando.")
                erro_encerramento = (
                    f"acao repetida {acoes_repetidas[chave]}x sem progresso: {chave}"
                )
                break

            # Notifica o widget: qual ferramenta ta rodando AGORA
            _widget_notify(passo_atual=ferramenta, state="running", computer_activity=_is_computer_activity_tool(ferramenta))

            r = _executar_passo(ferramenta, args)

            # FASE 26 - observar o resultado (se a ferramenta muda estado)
            observacao = _observar(objetivo, ferramenta, args, r["resultado"], r["erro"])
            _widget_notify(computer_activity=False)
            if observacao:
                print(f"[OBSERVER] sucesso={observacao.get('sucesso')} "
                      f"objetivo_atingido={observacao.get('objetivo_atingido')} "
                      f"motivo={str(observacao.get('motivo', ''))[:80]}")

            entrada = {
                "passo": passo_num,
                "ferramenta": ferramenta,
                "args": args,
                "motivo": motivo,
                "ok": r["ok"],
                "resultado": r["resultado"],
                "erro": r["erro"],
                "observacao": observacao,
                "timestamp": time.time(),
            }
            historico.append(entrada)

            # FASE 26 - verificar o objetivo com evidencia observavel
            verificacao = autonomy.verificar(objetivo, historico, observacao)
            entrada["verificacao"] = verificacao
            print(f"[VERIFICAR] atingido={verificacao.get('atingido')} "
                  f"confianca={verificacao.get('confianca')} "
                  f"motivo={str(verificacao.get('motivo', ''))[:100]}")

            # FASE 26 - recuperar de falhas com nova estrategia e limite explicito
            if not r["ok"]:
                rec = autonomy.recuperar(
                    ferramenta,
                    args,
                    r["erro"],
                    historico,
                    recuperacoes_usadas=recuperacoes_usadas,
                )
                recuperacoes_usadas += 1
                entrada["recuperacao"] = rec
                _bloquear_acao(acoes_bloqueadas, rec.get("acoes_bloqueadas"))
                _evento(task_id, "recuperacao", rec.get("motivo", ""), passo=passo_num)
                print(f"[RECUPERAR] desistir={rec.get('desistir')} "
                      f"motivo={str(rec.get('motivo', ''))[:100]}")
                if rec.get("desistir"):
                    erro_encerramento = rec.get("motivo", "recuperacao esgotada")
                    _persistir(task_id, historico=historico, passo_atual=passo_num)
                    break
                diretriz_recuperacao = rec.get("diretriz", "")

            # FASE 26 - persistir o passo (pausa/retomada e retomada apos crash)
            _persistir(
                task_id,
                historico=historico,
                passo_atual=passo_num,
                estado=task_store.ESTADO_EM_EXECUCAO,
            )
            _evento(task_id, "passo", f"{ferramenta} ok={r['ok']}", passo=passo_num)

            # Notifica o widget: historico atualizado
            _widget_notify(
                historico=[{"ferramenta": h["ferramenta"]} for h in historico],
                state="running",
            )

            if r["ok"]:
                erros_consecutivos = 0
                # A recuperacao funcionou: a diretriz deixa de ser necessaria
                # (as acoes bloqueadas continuam bloqueadas).
                diretriz_recuperacao = ""
                # Objetivo confirmado pelo observer: encerra com evidencia, sem esperar o planner.
                if verificacao.get("atingido") is True:
                    motivo_encerramento = f"objetivo verificado: {verificacao.get('motivo')}"
                    print(f"[VERIFICAR] objetivo atingido - encerrando: {motivo_encerramento}")
                    break
            else:
                erros_consecutivos += 1
                if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    print("[TASK] muitos erros consecutivos. Abortando.")
                    erro_encerramento = f"{erros_consecutivos} erros consecutivos sem recuperacao"
                    break

            continue

        print(f"[TASK] acao desconhecida: {acao}")
        erro_encerramento = erro_encerramento or f"acao desconhecida retornada pelo planner: {acao}"
        break

    print(f"\n[TASK] finalizando com {len(historico)} passos executados")

    if erro_encerramento and not motivo_encerramento:
        print(f"[TASK] encerrada com falha: {erro_encerramento}")
        _persistir(
            task_id,
            historico=historico,
            passo_atual=len(historico),
            estado=task_store.ESTADO_FALHOU,
            erro=erro_encerramento,
            terminado=True,
        )
        _evento(task_id, "falhou", erro_encerramento)
        return _resposta(
            "falhou", objetivo, historico, task_id,
            resultado_final=None,
            erro=erro_encerramento,
            motivo_encerramento=erro_encerramento,
        )

    resultado_final = _sintetizar(objetivo, historico)
    _persistir(
        task_id,
        historico=historico,
        passo_atual=len(historico),
        estado=task_store.ESTADO_CONCLUIDO,
        resultado_final=resultado_final,
        terminado=True,
    )
    _evento(task_id, "concluida", motivo_encerramento or "sintese final")

    return _resposta(
        "ok", objetivo, historico, task_id,
        resultado_final=resultado_final,
        motivo_encerramento=motivo_encerramento,
    )


# ============================================================
# FASE 26 - retomada de tasks persistidas
# ============================================================

def listar_tasks_pendentes(limite: int = 20) -> list:
    """Tasks que podem ser retomadas (pausadas, em execucao ou interrompidas)."""
    try:
        return task_store.tasks_retomaveis(limite=limite)
    except Exception as e:
        print(f"[STORE] erro ao listar tasks: {e}")
        return []


def retomar_task(task_id: str, max_passos: int | None = None) -> dict:
    """Retoma uma task persistida (pausa, reinicio do processo ou crash).

    Preserva objetivo, historico, observacoes, verificacoes e recuperacoes ja
    feitas: o planner recebe o historico completo e continua do passo seguinte.
    """
    try:
        registo = task_store.carregar_task(task_id)
    except Exception as e:
        return _resposta("erro", "", [], task_id, erro=f"erro ao carregar task: {e}")

    if not registo:
        return _resposta("erro", "", [], task_id, erro=f"task nao encontrada: {task_id}")

    estado = registo.get("estado")
    if estado not in task_store.ESTADOS_RETOMAVEIS:
        return _resposta(
            "erro",
            registo.get("objetivo", ""),
            registo.get("historico") or [],
            task_id,
            erro=f"task nao pode ser retomada (estado={estado})",
        )

    if estado == task_store.ESTADO_INTERROMPIDO:
        _evento(task_id, "retomada_apos_interrupcao", registo.get("erro") or "")

    # Retomar significa voltar a rodar: limpa cancelamento e pausa.
    resetar()
    resetar_pausa()

    historico = registo.get("historico") or []
    total = max_passos or registo.get("max_passos") or MAX_PASSOS_PADRAO
    total = max(int(total), len(historico) + PASSOS_EXTRA_AO_RETOMAR)

    _evento(task_id, "retomada", f"retomando do passo {len(historico) + 1}", passo=len(historico))

    return executar_task(
        registo.get("objetivo", ""),
        max_passos=total,
        task_id=task_id,
        historico=historico,
        passo_inicial=len(historico) + 1,
    )

