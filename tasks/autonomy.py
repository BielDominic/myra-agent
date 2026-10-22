# -*- coding: utf-8 -*-
"""FASE 26 - verificacao de objetivo e recuperacao de falhas.

Duas responsabilidades, ambas deterministicas (nao chamam LLM):

- ``verificar(objetivo, historico, observacao)``: decide se o objetivo foi
  atingido usando evidencia observavel. Nunca declara sucesso sem
  confirmacao: sem observacao a resposta e "indeterminada" e o planner
  continua no comando.
- ``recuperar(...)``: apos uma falha, decide se vale tentar de novo com
  outra estrategia (diretriz para o planner) ou se deve desistir com um
  motivo explicito. Tambem mantem a lista de acoes bloqueadas, para que a
  mesma ferramenta com os mesmos argumentos nao seja repetida.
"""
from __future__ import annotations

import json
import unicodedata

# Limites de recuperacao
MAX_TENTATIVAS_POR_ACAO = 2      # falhas da MESMA acao antes de bloquear
LIMITE_RECUPERACOES = 3          # tentativas de nova estrategia por task

# Siglas curtas usadas no prompt de recuperacao
SUGESTOES_POR_FERRAMENTA = {
    "browser_click_text": (
        "o clique por texto falhou; confirme o texto com browser_read_page "
        "(ou browser_get_tabs) antes de tentar outro alvo, ou use vision_click(descricao)"
    ),
    "browser_type_text": (
        "digitar por seletor falhou; leia a pagina para descobrir o campo correto "
        "ou use vision_type(descricao, texto)"
    ),
    "browser_new_tab": (
        "abrir nova aba falhou; confira browser_get_tabs e tente "
        "browser_navigate_active_tab"
    ),
    "browser_navigate_active_tab": (
        "a navegacao falhou; confira a URL (http/https completa) e as abas com "
        "browser_get_tabs"
    ),
    "browser_read_page": (
        "a leitura falhou; confirme a URL/aba com browser_get_tabs ou use "
        "browser_read_active_tab com url_contains"
    ),
    "browser_read_active_tab": (
        "a leitura da aba falhou; liste as abas com browser_get_tabs e indique "
        "url_contains"
    ),
    "browser_search_google": (
        "a pesquisa falhou; tente browser_search_google_visivel ou abra a URL de "
        "pesquisa com browser_new_tab"
    ),
    "vision_locate": (
        "a localizacao visual falhou; tire um novo screenshot (pc_screenshot) ou "
        "leia o DOM com read_page_structured"
    ),
    "vision_click": (
        "o clique visual falhou; localize o alvo com vision_locate e clique por "
        "coordenadas com pc_click"
    ),
    "vision_type": (
        "digitar visualmente falhou; clique no campo com vision_click antes de "
        "digitar, ou use browser_type_text com seletor"
    ),
    "pc_click": (
        "o clique no PC falhou; confirme a janela ativa com pc_get_active_window "
        "e foque a janela com pc_focus_window"
    ),
    "write_file": (
        "escrever o arquivo falhou; confirme o caminho com list_dir e use um "
        "caminho dentro do workspace"
    ),
    "read_file": (
        "ler o arquivo falhou; confirme o nome exato com list_dir"
    ),
    "delete_file": (
        "apagar o arquivo falhou; confirme o caminho exato com list_dir"
    ),
    "email_send": (
        "o envio falhou; confirme destinatario e assunto e tente novamente uma "
        "unica vez; se persistir, relate o erro ao usuario"
    ),
    "code_run": (
        "a execucao falhou; corrija o codigo com base no stderr antes de executar "
        "de novo"
    ),
}

SUGESTAO_PADRAO = (
    "use uma ferramenta DIFERENTE, com argumentos diferentes, ou divida o "
    "objetivo em passos menores"
)


def assinatura_acao(ferramenta: str, args: dict | list | None) -> str:
    """Assinatura estavel de uma acao (ferramenta + argumentos)."""
    try:
        args_str = json.dumps(args or {}, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        args_str = str(args)
    return f"{ferramenta}:{args_str}"


def contar_falhas(historico: list, assinatura: str) -> int:
    """Quantas vezes essa mesma acao ja falhou no historico."""
    total = 0
    for passo in historico or []:
        if passo.get("ok"):
            continue
        if assinatura_acao(passo.get("ferramenta", ""), passo.get("args")) == assinatura:
            total += 1
    return total


# ------------------------------------------------------------
# VERIFICACAO
# ------------------------------------------------------------

def _objetivo_exige_leitura_pagina(objetivo: str) -> bool:
    """Detecta pedidos explicitos para ler/extrair conteudo de uma pagina."""
    texto = unicodedata.normalize("NFKD", str(objetivo or "").casefold())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    marcadores = (
        "leia a pagina", "ler a pagina", "leia o conteudo", "ler o conteudo",
        "conteudo da pagina", "texto da pagina", "texto principal da pagina",
        "primeiro paragrafo", "paragrafo da pagina", "extraia o texto",
        "read the page", "read page content", "page content", "first paragraph",
        "extract the text", "read the main text",
    )
    return any(marcador in texto for marcador in marcadores)


def _objetivo_exige_interacao_pagina(objetivo: str) -> bool:
    """Detecta pedidos explicitos de clique, digitacao, selecao ou envio."""
    texto = unicodedata.normalize("NFKD", str(objetivo or "").casefold())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    marcadores = (
        "clique em", "clique no", "clique na", "clicar em", "clicar no",
        "clicar na", "pressione a tecla", "digite no campo", "digite no",
        "preencha o campo", "preencher o campo", "envie o formulario",
        "enviar o formulario", "selecione a opcao", "selecionar a opcao",
        "click the", "click on", "type into", "fill in", "submit the",
        "press the key", "select the option",
    )
    return any(marcador in texto for marcador in marcadores)


def _resultado_contem_conteudo_pagina(resultado) -> bool:
    """Retorna True apenas se a ferramenta trouxe texto de corpo, nao so URL/titulo."""
    if not isinstance(resultado, dict):
        return False
    texto = resultado.get("text")
    if isinstance(texto, str) and texto.strip():
        return True
    detalhe = resultado.get("result")
    if isinstance(detalhe, str):
        normalizado = detalhe.casefold()
        return "texto visivel:" in normalizado or "visible text:" in normalizado
    return False


def verificar(objetivo: str, historico: list, observacao: dict | None = None) -> dict:
    """Verifica se o objetivo foi atingido, sempre com base em evidencia.

    Returns:
        {
          "atingido": True | False | None,   # None = indeterminado, nao conclua
          "confianca": "alta" | "media" | "indeterminada",
          "motivo": str,
          "evidencia": str,
        }

    Regra central: sucesso so e declarado (atingido=True) quando o observer
    confirma *acao bem-sucedida* E *objetivo atingido*. Qualquer outro caso
    devolve False (evidencia negativa) ou None (sem evidencia).
    """
    if not historico:
        return {
            "atingido": None,
            "confianca": "indeterminada",
            "motivo": "nenhuma acao executada ainda",
            "evidencia": "",
        }

    ultimo = historico[-1]
    obs = observacao if observacao is not None else ultimo.get("observacao")
    if not isinstance(obs, dict):
        obs = None

    # 1) A propria execucao falhou -> evidencia negativa forte.
    if not ultimo.get("ok"):
        erro = ultimo.get("erro") or "erro sem detalhe"
        return {
            "atingido": False,
            "confianca": "alta",
            "motivo": f"a ultima acao falhou: {str(erro)[:200]}",
            "evidencia": f"{ultimo.get('ferramenta')}: {str(erro)[:200]}",
        }

    # 2) Resultado devolveu status de erro explicito (ex.: rotas do agent.py).
    resultado = ultimo.get("resultado")
    if isinstance(resultado, dict) and resultado.get("status") == "erro":
        detalhe = resultado.get("result") or resultado.get("erro") or "erro reportado"
        return {
            "atingido": False,
            "confianca": "alta",
            "motivo": f"a ferramenta reportou erro: {str(detalhe)[:200]}",
            "evidencia": f"{ultimo.get('ferramenta')}: {str(detalhe)[:200]}",
        }

    # 2.25) Navegar nao satisfaz um pedido explicito de leitura do corpo da pagina.
    #       O observer pode ser otimista ao ver a URL/titulo; exige evidencia de
    #       texto antes de aceitar sucesso para objetivos que pedem conteudo.
    ferramenta = ultimo.get("ferramenta", "")
    ferramentas_navegacao_leitura = {
        "browser_new_tab", "browser_navigate_active_tab",
        "browser_read_page", "browser_read_active_tab", "browser_get_tabs",
        "get_current_url",
    }
    exige_leitura = _objetivo_exige_leitura_pagina(objetivo)
    exige_interacao = _objetivo_exige_interacao_pagina(objetivo)
    if ferramenta in ferramentas_navegacao_leitura and exige_interacao:
        return {
            "atingido": False,
            "confianca": "alta",
            "motivo": "navegar/ler a pagina nao executa a interacao solicitada; continue com a ferramenta de clique ou digitacao adequada",
            "evidencia": str((resultado or {}).get("url", "") if isinstance(resultado, dict) else "")[:200],
        }
    if (
        ferramenta in {"browser_new_tab", "browser_navigate_active_tab"}
        and isinstance(resultado, dict)
        and resultado.get("status") == "ok"
        and exige_leitura
        and not _resultado_contem_conteudo_pagina(resultado)
    ):
        return {
            "atingido": False,
            "confianca": "alta",
            "motivo": "a navegacao foi concluida, mas o objetivo exige ler o conteudo da pagina; use browser_read_page ou browser_read_active_tab",
            "evidencia": str((resultado or {}).get("url", "") if isinstance(resultado, dict) else "")[:200],
        }
    if (
        ferramenta in {"browser_read_page", "browser_read_active_tab"}
        and isinstance(resultado, dict)
        and resultado.get("status") == "ok"
        and exige_leitura
        and not _resultado_contem_conteudo_pagina(resultado)
    ):
        return {
            "atingido": False,
            "confianca": "alta",
            "motivo": "a ferramenta de leitura nao retornou texto do corpo da pagina; nao confirme a extracao",
            "evidencia": str((resultado or {}).get("url", "") if isinstance(resultado, dict) else "")[:200],
        }

    if (
        ferramenta in {"browser_read_page", "browser_read_active_tab"}
        and exige_leitura
        and _resultado_contem_conteudo_pagina(resultado)
    ):
        return {
            "atingido": True,
            "confianca": "alta",
            "motivo": "a ferramenta retornou texto do corpo da pagina para o objetivo de leitura",
            "evidencia": str((resultado or {}).get("text") or (resultado or {}).get("result") or "")[:200],
        }

    # 2.5) Ferramentas de LEITURA SIMPLES: sucesso ja e prova suficiente.
    #      get_current_time, get_weather, etc retornam status=ok. Nao ha
    #      "observacao visual" possivel. Sem isto, o verifier cai no caso 4
    #      (None) e o planner repete a ferramenta -> loop.
    FERRAMENTAS_AUTO_CONFIRM = {
        "get_current_time", "get_weather", "read_notes", "list_dir",
        "read_file", "email_list", "email_read", "get_current_url",
        "browser_get_tabs", "read_page_structured",
        "save_note", "search_google_structured", "web_search_structured",
        "youtube_search", "youtube_channel_latest",
    }
    ferramenta = ultimo.get("ferramenta", "")
    if ferramenta in FERRAMENTAS_AUTO_CONFIRM:
        res = ultimo.get("resultado") or {}
        if isinstance(res, dict) and res.get("status") == "ok":
            # Obter a hora so confirma objetivos que realmente pedem hora/data.
            # Caso contrario, o planner pode encerrar uma tarefa de navegador
            # apos executar get_current_time sem sequer tentar abrir o Chrome.
            confirma_objetivo = True
            if ferramenta == "get_current_time":
                objetivo_lower = objetivo.casefold()
                termos_tempo = (
                    "hora", "horário", "que horas",
                    "current time", "what time", "data de hoje",
                    "date today", "today's date",
                )
                confirma_objetivo = any(t in objetivo_lower for t in termos_tempo)
            if confirma_objetivo:
                return {
                    "atingido": True,
                    "confianca": "alta",
                    "motivo": ferramenta + " retornou com sucesso",
                    "evidencia": str(res.get("result", ""))[:200],
                }

    # 3) Observacao do observer (LLM) sobre a ultima acao.
    if obs and obs.get("status") == "ok":
        sucesso = obs.get("sucesso")
        atingido = obs.get("objetivo_atingido")
        motivo_obs = str(obs.get("motivo", ""))[:250]

        if sucesso is False:
            return {
                "atingido": False,
                "confianca": "alta",
                "motivo": f"observer: a acao nao funcionou ({motivo_obs})",
                "evidencia": motivo_obs,
            }
        if atingido is True and sucesso is True:
            return {
                "atingido": True,
                "confianca": "alta",
                "motivo": f"observer confirmou o objetivo ({motivo_obs})",
                "evidencia": motivo_obs,
            }
        if atingido is False:
            return {
                "atingido": False,
                "confianca": "media",
                "motivo": f"observer: objetivo ainda nao atingido ({motivo_obs})",
                "evidencia": motivo_obs,
            }
        return {
            "atingido": None,
            "confianca": "indeterminada",
            "motivo": f"observer sem resposta conclusiva ({motivo_obs})",
            "evidencia": motivo_obs,
        }

    # 4) Sem observacao: nunca declare sucesso; deixe o planner decidir.
    return {
        "atingido": None,
        "confianca": "indeterminada",
        "motivo": "sem observacao confiavel para esta acao",
        "evidencia": "",
    }


# ------------------------------------------------------------
# RECUPERACAO
# ------------------------------------------------------------

def recuperar(
    ferramenta: str,
    args: dict | list | None,
    erro: str | None,
    historico: list,
    tentativas: int | None = None,
    limite_tentativas: int = MAX_TENTATIVAS_POR_ACAO,
    recuperacoes_usadas: int = 0,
    limite_recuperacoes: int = LIMITE_RECUPERACOES,
) -> dict:
    """Decide como recuperar de uma falha.

    Returns:
        {
          "recuperar": bool,          # vale tentar de novo com outra estrategia?
          "desistir": bool,           # encerrar a task com motivo explicito?
          "tentativas": int,          # falhas desta mesma acao
          "motivo": str,              # explicacao para o log/usuario
          "diretriz": str,            # texto injetado no prompt do planner
          "acoes_bloqueadas": [str],  # assinaturas que nao devem ser repetidas
        }
    """
    assinatura = assinatura_acao(ferramenta, args)
    falhas = contar_falhas(historico, assinatura) if tentativas is None else int(tentativas)
    # A acao atual ja esta no historico quando esta funcao e chamada; garante
    # pelo menos 1 falha contabilizada.
    falhas = max(1, falhas)
    sugestao = SUGESTOES_POR_FERRAMENTA.get(ferramenta, SUGESTAO_PADRAO)

    if falhas >= limite_tentativas:
        return {
            "recuperar": False,
            "desistir": True,
            "tentativas": falhas,
            "motivo": (
                f"acao bloqueada apos {falhas} falhas com os mesmos argumentos "
                f"({assinatura}): {str(erro or 'erro sem detalhe')[:200]}"
            ),
            "diretriz": "",
            "acoes_bloqueadas": [assinatura],
        }

    if recuperacoes_usadas >= limite_recuperacoes:
        return {
            "recuperar": False,
            "desistir": True,
            "tentativas": falhas,
            "motivo": (
                f"limite de {limite_recuperacoes} recuperacoes atingido; ultimo erro: "
                f"{str(erro or 'erro sem detalhe')[:200]}"
            ),
            "diretriz": "",
            "acoes_bloqueadas": [assinatura],
        }

    return {
        "recuperar": True,
        "desistir": False,
        "tentativas": falhas,
        "motivo": f"falha em {ferramenta}: {str(erro or 'erro sem detalhe')[:200]}",
        "diretriz": (
            f"A ultima acao falhou ({ferramenta}): {str(erro or 'erro sem detalhe')[:200]}. "
            f"NAO repita {assinatura}. Estrategia alternativa: {sugestao}."
        ),
        "acoes_bloqueadas": [assinatura],
    }


def resumo_recuperacoes(historico: list) -> str:
    """Resumo legivel das recuperacoes ja tentadas (para logs e sintese)."""
    linhas = []
    for passo in historico or []:
        rec = passo.get("recuperacao")
        if not rec:
            continue
        estado = "desistiu" if rec.get("desistir") else "nova tentativa"
        linhas.append(
            f"passo {passo.get('passo')}: {estado} - {str(rec.get('motivo', ''))[:150]}"
        )
    return "\n".join(linhas)
