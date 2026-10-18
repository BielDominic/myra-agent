# -*- coding: utf-8 -*-
"""Testes severos do registo de ferramentas do planner (tasks/simple_task.py).

Alvo: ``FERRAMENTAS_DISPONIVEIS``, ``FERRAMENTAS_DESCRICOES``,
``registrar_ferramenta``, ``_FERRAMENTAS_LEGADAS_COM_BRIDGE``,
``FERRAMENTAS_OBSERVAVEIS``, ``_deve_observar`` e o consumidor directo do
registo (``_executar_passo``).

Regras de seguranca respeitadas:
  * nenhuma ligacao de rede: ``helpers.sem_rede()`` activo em todos os testes;
  * nenhuma ferramenta real e chamada: o registo e substituido por fakes
    deterministicos (as 53 ferramentas reais so sao inspeccionadas, nunca
    invocadas);
  * bancos/temporarios redirecionados para tmp por ``helpers.CasoBase``;
  * ``time.sleep`` e sempre mockado (o retry de ``_executar_passo`` dorme 1s)
    e o registo do planner e guardado/restaurado em cada teste.
"""
from __future__ import annotations

import inspect
import re
import time
import unittest
from unittest import mock

from tasks import simple_task
from tests import helpers


# ============================================================
# Importacao unica do agent.py (e o import que popula o registo do planner).
# O ambiente fica isolado durante toda a vida do modulo de teste.
# ============================================================
_AMBIENTE_MODULO = helpers.AmbienteIsolado()
_TMP_MODULO = _AMBIENTE_MODULO.__enter__()
AGENT = helpers.importar_agent()


def tearDownModule():
    _AMBIENTE_MODULO.__exit__(None, None, None)


# ============================================================
# Factos verificados do registo publicado pelo agent.py
# ============================================================
GRUPOS_ESPERADOS = {
    "browser_bridge": frozenset({
        "browser_get_tabs", "browser_read_active_tab", "browser_read_page",
        "browser_navigate_active_tab", "browser_new_tab", "browser_close_tab",
        "browser_type_text", "browser_click_text", "browser_scroll",
        "browser_search_google_visivel", "browser_search_google", "browser_wait",
    }),
    "visao_pc": frozenset({
        "vision_locate", "vision_click", "vision_type",
        "pc_move_mouse", "pc_click", "pc_type_text", "pc_press_key",
        "pc_hotkey", "pc_screenshot", "pc_get_windows",
        "pc_get_active_window", "pc_focus_window",
    }),
    "ficheiros": frozenset({
        "write_file", "read_file", "list_dir", "delete_file",
        "create_dir", "move_file", "search_in_files",
    }),
    "codigo": frozenset({"code_run", "run_python"}),
    "email": frozenset({
        "email_list", "email_read", "email_send", "email_search", "email_reply",
    }),
    "web_youtube_estruturado": frozenset({
        "search_google_structured", "web_search_structured", "youtube_search",
        "youtube_channel_latest", "get_current_url", "read_page_structured",
    }),
    "utilitarios_sistema": frozenset({
        "web_search", "get_weather", "get_current_time", "youtube_transcript",
        "responder", "save_note", "read_notes",
    }),
    "rea": frozenset({"rea_analyze_javascript", "rea_status"}),
}

TAMANHOS_ESPERADOS = {
    "browser_bridge": 12,
    "visao_pc": 12,
    "ficheiros": 7,
    "codigo": 2,
    "email": 5,
    "web_youtube_estruturado": 6,
    "utilitarios_sistema": 7,
    "rea": 2,
}

NOMES_ESPERADOS = frozenset(
    nome for grupo in GRUPOS_ESPERADOS.values() for nome in grupo
)
TOTAL_FERRAMENTAS = 53

# Aliases legados (rotas HTTP antigas) que o registo do planner ja nao expoe.
LEGADOS_ESPERADOS = frozenset({
    "open_url", "read_page", "click_element", "type_text",
    "search_google", "wait",
})

# Ferramentas de pesquisa que o prompt esconde quando o objetivo e navegar.
# Copia deliberada do conjunto de producao: se ele mudar, o teste falha.
OCULTAS_EM_NAVEGACAO = frozenset({
    "web_search_structured", "youtube_search", "youtube_summarize",
    "youtube_ask", "youtube_transcript", "youtube_channel_latest",
    "search_google", "search_google_structured", "get_current_time",
})

# FERRAMENTAS_OBSERVAVEIS inclui nomes que existem apenas como rotas HTTP do
# agent.py (nunca foram registados como ferramentas do planner). Estao
# documentados aqui de forma explicita: qualquer nome NOVO que apareca no
# observavel sem estar registado faz o teste falhar.
OBSERVAVEIS_NAO_REGISTADOS_DOCUMENTADOS = frozenset({
    "pc_double_click", "pc_right_click",
    "email_delete_by_search", "email_mark_read", "email_mark_unread",
    "email_move",
})

TOTAL_OBSERVAVEIS = 27

# Nomes das ferramentas renderizados no prompt: "- nome: descricao".
_RE_LINHA_FERRAMENTA = re.compile(r"^- ([A-Za-z0-9_]+):", re.M)
_RE_NOME_SEGURO = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class _BaseRegisto(helpers.CasoBase):
    """CasoBase + rede bloqueada + registo do planner guardado/restaurado."""

    def setUp(self):
        super().setUp()
        self._ferramentas_originais = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        self._descricoes_originais = dict(simple_task.FERRAMENTAS_DESCRICOES)
        self.addCleanup(self._restaurar_registo)

        self._rede = helpers.sem_rede()
        self._rede.__enter__()
        self.addCleanup(self._sair_sem_rede)

    def _sair_sem_rede(self):
        self._rede.__exit__(None, None, None)

    def _restaurar_registo(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self._ferramentas_originais)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(self._descricoes_originais)

    def _registar(self, nome, fn, descricao="ferramenta de teste"):
        simple_task.registrar_ferramenta(nome, fn, descricao)


# ============================================================
# 1) Contrato do registo publicado pelo agent.py
# ============================================================

class RegistoRealTestCase(_BaseRegisto):
    """O registo depois de importar agent.py tem de ser exactamente o esperado."""

    def test_o_registo_inspeccionado_e_o_mesmo_que_o_agent_usa(self):
        """Garante que nao estamos a testar uma copia do registo."""
        self.assertIs(AGENT._simple_task_module, simple_task)
        self.assertIs(
            AGENT._simple_task_module.FERRAMENTAS_DISPONIVEIS,
            simple_task.FERRAMENTAS_DISPONIVEIS,
        )
        self.assertIs(AGENT.registrar_ferramenta, simple_task.registrar_ferramenta)
        self.assertEqual(AGENT.executar_task.__module__, simple_task.__name__)

    # -- item (1): conjunto exacto, ordenado --------------------------------
    def test_registo_exato_de_53_ferramentas(self):
        reais = sorted(simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertEqual(
            len(reais), TOTAL_FERRAMENTAS,
            f"o registo tem {len(reais)} ferramentas, esperadas {TOTAL_FERRAMENTAS}",
        )
        self.assertEqual(reais, sorted(NOMES_ESPERADOS))
        # conjunto exacto: nada a mais, nada a menos
        self.assertEqual(
            set(reais) - set(NOMES_ESPERADOS), set(),
            "ferramentas inesperadas no registo",
        )
        self.assertEqual(
            set(NOMES_ESPERADOS) - set(reais), set(),
            "ferramentas em falta no registo",
        )

    def test_grupos_somam_53_e_nao_se_sobrepoem(self):
        todos: list[str] = []
        for grupo, nomes in GRUPOS_ESPERADOS.items():
            with self.subTest(grupo=grupo):
                self.assertEqual(len(nomes), TAMANHOS_ESPERADOS[grupo])
                # todo o nome do grupo tem de estar registado
                self.assertEqual(
                    nomes - set(simple_task.FERRAMENTAS_DISPONIVEIS), frozenset(),
                    f"ferramentas de {grupo} nao registadas",
                )
            todos.extend(nomes)
        self.assertEqual(len(todos), TOTAL_FERRAMENTAS, "grupos sobrepostos ou incompletos")
        self.assertEqual(frozenset(todos), NOMES_ESPERADOS)
        self.assertEqual(frozenset(todos), frozenset(simple_task.FERRAMENTAS_DISPONIVEIS))

    # -- item (2): descricao por ferramenta --------------------------------
    def test_descricoes_uma_por_ferramenta_e_utilizaveis_no_prompt(self):
        disponiveis = set(simple_task.FERRAMENTAS_DISPONIVEIS)
        descricoes = simple_task.FERRAMENTAS_DESCRICOES
        self.assertEqual(set(descricoes), disponiveis, "descricao orfa ou em falta")
        for nome in sorted(disponiveis):
            with self.subTest(ferramenta=nome):
                descricao = descricoes[nome]
                self.assertIsInstance(descricao, str)
                self.assertTrue(descricao.strip(), f"{nome} sem descricao")
                self.assertGreaterEqual(len(descricao.strip()), 10)
                # uma descricao multi-linha quebraria o formato "- nome: desc"
                self.assertNotIn("\n", descricao)
                self.assertNotIn("\r", descricao)
                self.assertLessEqual(len(descricao), 400)

    # -- item (3): chamaveis com assinatura valida -------------------------
    def test_todas_as_ferramentas_sao_chamaveis_com_assinatura_valida(self):
        for nome, fn in sorted(simple_task.FERRAMENTAS_DISPONIVEIS.items()):
            with self.subTest(ferramenta=nome):
                self.assertTrue(callable(fn), f"{nome} nao e chamavel")
                try:
                    assinatura = inspect.signature(fn)
                except (TypeError, ValueError) as exc:  # pragma: no cover - defensivo
                    self.fail(f"{nome} sem assinatura inspeccionavel: {exc}")
                for parametro in assinatura.parameters.values():
                    self.assertTrue(parametro.name, f"{nome} tem parametro sem nome")
                    self.assertTrue(
                        parametro.name.isidentifier(),
                        f"{nome}: parametro invalido {parametro.name!r}",
                    )
                    # _executar_passo chama fn(**args): *args posicional isolado
                    # ou POSITIONAL_ONLY obrigatorio quebrariam o contrato.
                    self.assertIsNot(
                        parametro.kind, inspect.Parameter.VAR_POSITIONAL,
                        f"{nome} usa *args posicional",
                    )
                    self.assertIsNot(
                        parametro.kind, inspect.Parameter.POSITIONAL_ONLY,
                        f"{nome} usa parametro POSITIONAL_ONLY",
                    )

    # -- item (4): nomes seguros para entrar num prompt --------------------
    def test_nomes_sao_ascii_minusculos_e_sem_caracteres_perigosos(self):
        for nome in sorted(simple_task.FERRAMENTAS_DISPONIVEIS):
            with self.subTest(ferramenta=nome):
                self.assertIsInstance(nome, str)
                self.assertTrue(nome, "nome vazio no registo")
                self.assertTrue(nome.isascii(), f"{nome} nao e ASCII")
                self.assertRegex(nome, _RE_NOME_SEGURO)
                self.assertEqual(nome, nome.strip())
                for perigo in (" ", "\t", "\n", ":", "-", '"', "'", "`", "{", "}", "\\"):
                    self.assertNotIn(perigo, nome)

    # -- item (5): aliases legados nao coexistem com o bridge --------------
    def test_aliases_legados_nao_coexistem_com_as_versoes_bridge(self):
        mapa = simple_task._FERRAMENTAS_LEGADAS_COM_BRIDGE
        self.assertEqual(frozenset(mapa), LEGADOS_ESPERADOS)
        for legado, equivalentes in sorted(mapa.items()):
            with self.subTest(legado=legado):
                self.assertNotIn(
                    legado, simple_task.FERRAMENTAS_DISPONIVEIS,
                    f"{legado} continua exposta ao planner apesar do bridge",
                )
                self.assertNotIn(legado, simple_task.FERRAMENTAS_DESCRICOES)
                self.assertTrue(
                    equivalentes & set(simple_task.FERRAMENTAS_DISPONIVEIS),
                    f"nenhuma versao bridge de {legado} esta registada",
                )

    def test_mapa_de_legados_tem_estrutura_valida(self):
        mapa = simple_task._FERRAMENTAS_LEGADAS_COM_BRIDGE
        self.assertIsInstance(mapa, dict)
        for legado, equivalentes in mapa.items():
            with self.subTest(legado=legado):
                self.assertIsInstance(legado, str)
                self.assertTrue(legado.isidentifier())
                self.assertIsInstance(equivalentes, (set, frozenset))
                self.assertTrue(equivalentes, f"{legado} sem equivalentes bridge")
                for nome_bridge in equivalentes:
                    self.assertIsInstance(nome_bridge, str)
                    self.assertTrue(nome_bridge.isidentifier())
                    self.assertNotEqual(nome_bridge, legado)
                    self.assertIn(
                        nome_bridge, simple_task.FERRAMENTAS_DISPONIVEIS,
                        f"{nome_bridge} (bridge de {legado}) nao esta registada",
                    )
        # nenhum nome legado e, ao mesmo tempo, nome bridge
        todos_bridge = {n for v in mapa.values() for n in v}
        self.assertEqual(frozenset(mapa) & todos_bridge, frozenset())

    # -- item (6): observaveis so com nomes registados ou documentados -----
    def test_ferramentas_observaveis_so_tem_registados_ou_documentados(self):
        observaveis = simple_task.FERRAMENTAS_OBSERVAVEIS
        self.assertIsInstance(observaveis, (set, frozenset))
        self.assertEqual(len(observaveis), TOTAL_OBSERVAVEIS)
        for nome in observaveis:
            self.assertIsInstance(nome, str)
            self.assertTrue(nome)
            self.assertTrue(nome.isascii())
            self.assertTrue(nome.isidentifier())
        nao_registados = frozenset(observaveis) - frozenset(simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertEqual(
            nao_registados, OBSERVAVEIS_NAO_REGISTADOS_DOCUMENTADOS,
            "FERRAMENTAS_OBSERVAVEIS ganhou/perdeu nomes nao registados; "
            "actualize a lista documentada (ou registe a ferramenta)",
        )
        # as restantes observaveis TEM de estar registadas
        self.assertEqual(
            len(frozenset(observaveis) & frozenset(simple_task.FERRAMENTAS_DISPONIVEIS)),
            TOTAL_OBSERVAVEIS - len(OBSERVAVEIS_NAO_REGISTADOS_DOCUMENTADOS),
        )

    def test_deve_observar_apenas_para_o_conjunto_observavel(self):
        observaveis_registadas = [
            nome for nome in simple_task.FERRAMENTAS_OBSERVAVEIS
            if nome in simple_task.FERRAMENTAS_DISPONIVEIS
        ]
        self.assertTrue(observaveis_registadas, "nenhuma observavel registada")
        for nome in observaveis_registadas:
            with self.subTest(ferramenta=nome):
                self.assertIs(simple_task._deve_observar(nome), True)

        # nomes documentados mas nunca registados: o observador continua a
        # responder True (entradas mortas, sem efeito pratico).
        for nome in sorted(OBSERVAVEIS_NAO_REGISTADOS_DOCUMENTADOS):
            with self.subTest(ferramenta=nome):
                self.assertIs(simple_task._deve_observar(nome), True)

        nao_observaveis = sorted(
            set(simple_task.FERRAMENTAS_DISPONIVEIS) - set(simple_task.FERRAMENTAS_OBSERVAVEIS)
        )
        self.assertTrue(nao_observaveis)
        for nome in nao_observaveis:
            with self.subTest(ferramenta=nome):
                self.assertIs(simple_task._deve_observar(nome), False)

    def test_deve_observar_e_robusto_a_nomes_estranhos(self):
        estranhos = [
            "", "  ", " ", "nao_existe_zzz", "WRITE_FILE", "Write_File",
            " write_file", "write_file ", "write_file\n", "write\u00adfile",
            "write_file\x00", "../../etc/passwd", "write_file;rm -rf /",
            "ferramenta_\U0001F600", "\u00e9criture", "a" * 5000,
            None, 0, 1, -1, 3.14, True, b"write_file",
        ]
        for valor in estranhos:
            with self.subTest(valor=repr(valor)):
                try:
                    resultado = simple_task._deve_observar(valor)
                except Exception as exc:  # noqa: BLE001
                    self.fail(
                        f"_deve_observar({valor!r}) levantou "
                        f"{type(exc).__name__}: {exc}"
                    )
                self.assertIs(resultado, False)

    # -- nomes do registo chegam ao prompt do planner -----------------------
    def _prompt_para(self, objetivo: str, historico=None) -> str:
        capturado: dict[str, str] = {}

        def _llm_falso(prompt, system="", timeout=120):
            capturado["prompt"] = prompt
            return '{"acao": "finalizar", "motivo": "sem mais passos"}'

        with mock.patch.object(simple_task, "_llm", _llm_falso):
            decisao = simple_task._decidir_proximo_passo(objetivo, list(historico or []))
        self.assertEqual(decisao.get("acao"), "finalizar")
        self.assertIn("prompt", capturado, "_llm nao foi chamado")
        return capturado["prompt"]

    def test_prompt_lista_as_53_ferramentas_com_a_sua_descricao(self):
        prompt = self._prompt_para("some dois numeros e diga o resultado")
        nomes_no_prompt = _RE_LINHA_FERRAMENTA.findall(prompt)
        self.assertEqual(len(nomes_no_prompt), len(set(nomes_no_prompt)), "nome duplicado")
        self.assertEqual(
            frozenset(nomes_no_prompt), frozenset(simple_task.FERRAMENTAS_DISPONIVEIS)
        )
        for nome, descricao in sorted(simple_task.FERRAMENTAS_DESCRICOES.items()):
            with self.subTest(ferramenta=nome):
                self.assertIn(f"- {nome}: {descricao}", prompt)

    def test_prompt_de_navegacao_esconde_ferramentas_de_pesquisa(self):
        prompt = self._prompt_para("abrir o site example.com no navegador")
        nomes_no_prompt = frozenset(_RE_LINHA_FERRAMENTA.findall(prompt))
        escondidas = OCULTAS_EM_NAVEGACAO & frozenset(simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertTrue(escondidas, "nenhuma ferramenta de pesquisa registada")
        self.assertEqual(nomes_no_prompt, frozenset(simple_task.FERRAMENTAS_DISPONIVEIS) - escondidas)
        for nome in sorted(escondidas):
            with self.subTest(ferramenta=nome):
                self.assertNotIn(f"- {nome}:", prompt)
                # continua registada: so sai do prompt de navegacao
                self.assertIn(nome, simple_task.FERRAMENTAS_DISPONIVEIS)


# ============================================================
# 2) Contrato de registrar_ferramenta
# ============================================================

class RegistrarFerramentaTestCase(_BaseRegisto):
    """registrar_ferramenta: idempotencia, aliases legados e entradas invalidas."""

    def setUp(self):
        super().setUp()
        # registo limpo: torna o resultado independente do estado do agent.py
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()

    # -- item (7): mesmo nome duas vezes -----------------------------------
    def test_registar_o_mesmo_nome_duas_vezes_nao_duplica(self):
        def primeira(**kwargs):
            return {"status": "ok", "result": "primeira"}

        def segunda(**kwargs):
            return {"status": "ok", "result": "segunda"}

        self._registar("minha_ferramenta", primeira, "descricao 1")
        self._registar("minha_ferramenta", segunda, "descricao 2")
        self._registar("minha_ferramenta", segunda, "descricao 2")

        self.assertEqual(list(simple_task.FERRAMENTAS_DISPONIVEIS), ["minha_ferramenta"])
        self.assertEqual(list(simple_task.FERRAMENTAS_DESCRICOES), ["minha_ferramenta"])
        self.assertIs(simple_task.FERRAMENTAS_DISPONIVEIS["minha_ferramenta"], segunda)
        self.assertEqual(simple_task.FERRAMENTAS_DESCRICOES["minha_ferramenta"], "descricao 2")

    def test_registo_sem_descricao_preserva_a_descricao_anterior(self):
        """Comportamento actual: descricao vazia nao limpa a descricao antiga."""
        self._registar("alvo", lambda **kw: None, "descricao original")
        self._registar("alvo", lambda **kw: None, "")
        self.assertEqual(simple_task.FERRAMENTAS_DESCRICOES["alvo"], "descricao original")

    def test_descricao_vazia_ou_none_nao_cria_entrada_de_descricao(self):
        for descricao in ("", None):
            with self.subTest(descricao=repr(descricao)):
                simple_task.FERRAMENTAS_DISPONIVEIS.clear()
                simple_task.FERRAMENTAS_DESCRICOES.clear()
                self.assertIsNone(
                    simple_task.registrar_ferramenta("sem_desc", lambda **kw: None, descricao)
                )
                self.assertIn("sem_desc", simple_task.FERRAMENTAS_DISPONIVEIS)
                self.assertNotIn("sem_desc", simple_task.FERRAMENTAS_DESCRICOES)
                self.assertEqual(simple_task.FERRAMENTAS_DESCRICOES, {})

    def test_descricao_omitida_e_aceite(self):
        self.assertIsNone(simple_task.registrar_ferramenta("so_nome", lambda **kw: None))
        self.assertIn("so_nome", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertNotIn("so_nome", simple_task.FERRAMENTAS_DESCRICOES)

    # -- item (7): a versao bridge remove o alias legado -------------------
    def test_registar_bridge_remove_o_alias_legado(self):
        mapa = simple_task._FERRAMENTAS_LEGADAS_COM_BRIDGE
        for legado, equivalentes in sorted(mapa.items()):
            for nome_bridge in sorted(equivalentes):
                with self.subTest(legado=legado, bridge=nome_bridge):
                    simple_task.FERRAMENTAS_DISPONIVEIS.clear()
                    simple_task.FERRAMENTAS_DESCRICOES.clear()
                    self._registar(legado, lambda **kw: None, f"legado {legado}")
                    self.assertIn(legado, simple_task.FERRAMENTAS_DISPONIVEIS)

                    self._registar(nome_bridge, lambda **kw: None, f"bridge {nome_bridge}")

                    self.assertNotIn(legado, simple_task.FERRAMENTAS_DISPONIVEIS)
                    self.assertNotIn(legado, simple_task.FERRAMENTAS_DESCRICOES)
                    self.assertIn(nome_bridge, simple_task.FERRAMENTAS_DISPONIVEIS)
                    self.assertIn(nome_bridge, simple_task.FERRAMENTAS_DESCRICOES)

    def test_apenas_um_equivalente_bridge_basta_para_remover_o_legado(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("open_url", lambda **kw: None, "abre url")
        self._registar("browser_navigate_active_tab", lambda **kw: None, "navega")
        self.assertNotIn("open_url", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertNotIn("open_url", simple_task.FERRAMENTAS_DESCRICOES)

    def test_legado_permanece_quando_nao_existe_versao_bridge(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("open_url", lambda **kw: None, "abre url")
        self._registar("read_page", lambda **kw: None, "le pagina")
        self._registar("write_file", lambda **kw: None, "escreve ficheiro")
        self.assertIn("open_url", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertIn("read_page", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertIn("write_file", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertEqual(
            sorted(simple_task.FERRAMENTAS_DISPONIVEIS),
            ["open_url", "read_page", "write_file"],
        )

    def test_bridge_remove_apenas_o_seu_proprio_legado(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("open_url", lambda **kw: None, "abre url")
        self._registar("click_element", lambda **kw: None, "clica")
        self._registar("browser_new_tab", lambda **kw: None, "nova aba")
        self.assertNotIn("open_url", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertIn("click_element", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertIn("click_element", simple_task.FERRAMENTAS_DESCRICOES)

    # -- item (8): o legado nao volta a entrar -----------------------------
    def test_legado_nao_volta_a_entrar_depois_do_bridge(self):
        mapa = simple_task._FERRAMENTAS_LEGADAS_COM_BRIDGE
        for legado, equivalentes in sorted(mapa.items()):
            with self.subTest(legado=legado):
                simple_task.FERRAMENTAS_DISPONIVEIS.clear()
                simple_task.FERRAMENTAS_DESCRICOES.clear()
                for nome_bridge in sorted(equivalentes):
                    self._registar(nome_bridge, lambda **kw: None, "bridge")

                # tentativa explicita de reintroduzir o legado
                self._registar(legado, lambda **kw: None, "legado reintroduzido")

                self.assertNotIn(legado, simple_task.FERRAMENTAS_DISPONIVEIS)
                self.assertNotIn(legado, simple_task.FERRAMENTAS_DESCRICOES)
                for nome_bridge in sorted(equivalentes):
                    self.assertIn(nome_bridge, simple_task.FERRAMENTAS_DISPONIVEIS)

    def test_legado_reintroduzido_com_o_bridge_removido_entra(self):
        """Contraprova do item (8): sem bridge, o legado e aceite normalmente."""
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("open_url", lambda **kw: None, "abre url")
        self.assertIn("open_url", simple_task.FERRAMENTAS_DISPONIVEIS)
        self.assertEqual(simple_task.FERRAMENTAS_DESCRICOES["open_url"], "abre url")

    # -- entradas invalidas ------------------------------------------------
    def test_registo_nao_valida_nome_nem_tipo_de_descricao(self):
        """Documenta a ausencia de validacao no registo (evidencia de robustez).

        O registo publicado pelo agent.py passa em
        ``test_nomes_sao_ascii_minusculos_e_sem_caracteres_perigosos``; este
        teste mostra que a validacao nao existe em ``registrar_ferramenta``.
        """
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        for nome in ("", " ", "nome com espaco", "NOME-MAIUSCULO", "acentuado\u00e7\u00e3o"):
            with self.subTest(nome=repr(nome)):
                simple_task.FERRAMENTAS_DISPONIVEIS.clear()
                simple_task.FERRAMENTAS_DESCRICOES.clear()
                self._registar(nome, lambda **kw: {"status": "ok"}, "descricao")
                self.assertIn(nome, simple_task.FERRAMENTAS_DISPONIVEIS)
                self.assertIn(nome, simple_task.FERRAMENTAS_DESCRICOES)

        # descricao de tipo errado e aceite tal e qual
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("tipo_errado", lambda **kw: None, 12345)
        self.assertEqual(simple_task.FERRAMENTAS_DESCRICOES["tipo_errado"], 12345)

    def test_ferramenta_sem_funcao_nao_derruba_o_executor(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("quebrada", None, "registada sem funcao")
        with mock.patch.object(simple_task.time, "sleep", new=lambda *a, **k: None):
            resultado = simple_task._executar_passo("quebrada", {})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["resultado"], None)
        self.assertIn("TypeError", resultado["erro"])

    def test_nome_de_ferramenta_registado_colide_com_legado_nao_registado(self):
        """Registar legado antes do bridge e depois registar outro nome nao o remove."""
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self._registar("wait", lambda **kw: None, "espera")
        self._registar("browser_scroll", lambda **kw: None, "rola")
        self._registar("browser_type_text", lambda **kw: None, "digita")
        self.assertEqual(
            sorted(simple_task.FERRAMENTAS_DISPONIVEIS),
            ["browser_scroll", "browser_type_text", "wait"],
        )


# ============================================================
# 3) Execucao de passos: nenhuma excepcao pode escapar
# ============================================================

class ExecutarPassoTestCase(_BaseRegisto):
    """_executar_passo: contrato de retorno, retries exactos e contencao de erros."""

    def setUp(self):
        super().setUp()
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        self.dormidas: list[float] = []
        self._patch_sleep = mock.patch.object(
            simple_task.time, "sleep", new=self._dormir
        )
        self._patch_sleep.start()
        self.addCleanup(self._patch_sleep.stop)

    def _dormir(self, segundos=0):
        self.dormidas.append(segundos)

    def _validar_forma(self, resultado):
        self.assertIsInstance(resultado, dict, f"esperado dict, veio {type(resultado)}")
        self.assertEqual(set(resultado), {"ok", "resultado", "erro"})
        self.assertIsInstance(resultado["ok"], bool)

    # -- ferramenta desconhecida -------------------------------------------
    def test_ferramenta_desconhecida_devolve_erro_estruturado(self):
        casos = [
            "nao_existe_zzz", "", "   ", "\U0001F600", "a" * 5000,
            "browser_new_tab ", " browser_new_tab", "BROWSER_NEW_TAB",
            "open_url; rm -rf /", "../../etc/passwd", "write_file\x00",
            None, 0, 123, 3.14, True, b"write_file",
        ]
        for nome in casos:
            with self.subTest(nome=repr(nome)):
                resultado = simple_task._executar_passo(nome, {})
                self._validar_forma(resultado)
                self.assertFalse(resultado["ok"])
                self.assertIsNone(resultado["resultado"])
                self.assertIsInstance(resultado["erro"], str)
                self.assertIn("ferramenta desconhecida", resultado["erro"])
        # ferramenta desconhecida nao tenta de novo nem dorme
        self.assertEqual(self.dormidas, [])

    def test_executar_passo_com_args_fora_do_contrato_nao_propaga(self):
        """``args`` tem de ser dict; outro tipo e contido e devolvido como erro.

        O primeiro ponto de falha e a linha de diagnostico
        (``list(args.keys())``), logo o erro esperado e AttributeError; para um
        dict sem os argumentos obrigatorios e TypeError. O que importa aqui:
        nada propaga, a ferramenta nunca corre e o erro vem preenchido.
        """
        chamadas = []

        def fake(obrigatorio):
            chamadas.append(obrigatorio)
            return {"status": "ok"}

        self._registar("fake", fake)
        for args in ([], None, "texto", 7, 3.14, b"x", True):
            with self.subTest(args=repr(args)):
                try:
                    resultado = simple_task._executar_passo("fake", args)
                except Exception as exc:  # noqa: BLE001
                    self.fail(
                        f"_executar_passo(args={args!r}) propagou "
                        f"{type(exc).__name__}: {exc}"
                    )
                self._validar_forma(resultado)
                self.assertFalse(resultado["ok"])
                self.assertIsNone(resultado["resultado"])
                self.assertIsInstance(resultado["erro"], str)
                self.assertTrue(resultado["erro"])
                self.assertTrue(
                    any(t in resultado["erro"] for t in ("AttributeError", "TypeError")),
                    f"erro inesperado para args={args!r}: {resultado['erro']!r}",
                )
                self.assertEqual(len(self.dormidas), 2, "2 tentativas em cada caso")
                self.dormidas.clear()
        self.assertEqual(chamadas, [], "a ferramenta nao devia ter corrido")

    def test_argumento_obrigatorio_em_falta_nao_propaga(self):
        self._registar("fake", lambda obrigatorio: {"status": "ok"})
        resultado = simple_task._executar_passo("fake", {})
        self._validar_forma(resultado)
        self.assertFalse(resultado["ok"])
        self.assertIn("TypeError", resultado["erro"])
        self.assertEqual(len(self.dormidas), 2, "devem ser 2 tentativas")

    # -- excepcoes ---------------------------------------------------------
    def test_excecao_da_ferramenta_e_contida_com_exactamente_duas_tentativas(self):
        chamadas = []

        def explode(**kwargs):
            chamadas.append(kwargs)
            raise ValueError("boom de proposito")

        self._registar("explode", explode)
        resultado = simple_task._executar_passo("explode", {"a": 1})

        self._validar_forma(resultado)
        self.assertFalse(resultado["ok"])
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(resultado["erro"], "ValueError: boom de proposito")
        self.assertEqual(len(chamadas), 2, "devem ser exactamente 2 tentativas")
        self.assertEqual(chamadas, [{"a": 1}, {"a": 1}])
        self.assertEqual(self.dormidas, [1, 1], "1s entre tentativas")

    def test_tipos_de_excepcao_diversos_nao_propagam(self):
        def levantar(exc):
            def _fn(**kwargs):
                raise exc
            return _fn

        casos = [
            ValueError("v"), TypeError("t"), KeyError("k"), RuntimeError("r"),
            OSError("rede bloqueada"), RecursionError("r"),
            MemoryError("m"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "x"),
        ]
        for indice, exc in enumerate(casos):
            nome = f"levanta_{indice}"
            with self.subTest(excecao=type(exc).__name__):
                self._registar(nome, levantar(exc))
                resultado = simple_task._executar_passo(nome, {})
                self._validar_forma(resultado)
                self.assertFalse(resultado["ok"])
                self.assertIsInstance(resultado["erro"], str)
                self.assertIn(type(exc).__name__, resultado["erro"])

    # -- erro declarado pela propria ferramenta ----------------------------
    def test_erro_declarado_pela_ferramenta_faz_duas_tentativas(self):
        chamadas = []

        def devolve_erro(**kwargs):
            chamadas.append(kwargs)
            return {"status": "erro", "result": "quebrou de proposito"}

        self._registar("devolve_erro", devolve_erro)
        resultado = simple_task._executar_passo("devolve_erro", {})

        self._validar_forma(resultado)
        self.assertFalse(resultado["ok"])
        self.assertIsNone(resultado["resultado"])
        self.assertEqual(resultado["erro"], "quebrou de proposito")
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(self.dormidas, [1, 1])

    def test_erro_sem_campo_result_usa_mensagem_padrao(self):
        self._registar("erro_seco", lambda **kw: {"status": "erro"})
        resultado = simple_task._executar_passo("erro_seco", {})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["erro"], "erro desconhecido")
        self.assertIsNotNone(resultado["erro"])

    def test_erro_com_result_none_usa_o_none_sem_rebentar(self):
        self._registar("erro_none", lambda **kw: {"status": "erro", "result": None})
        resultado = simple_task._executar_passo("erro_none", {})
        self.assertFalse(resultado["ok"])
        self.assertIsNone(resultado["erro"])

    def test_erro_com_result_de_tipo_estranho_e_repassado(self):
        for valor in (123, ["a"], {"x": 1}, b"bytes", "\U0001F600"):
            with self.subTest(valor=repr(valor)):
                nome = "erro_estranho"
                self._registar(nome, lambda **kw: {"status": "erro", "result": valor})
                resultado = simple_task._executar_passo(nome, {})
                self.assertFalse(resultado["ok"])
                self.assertEqual(resultado["erro"], valor)

    # -- ferramenta lenta --------------------------------------------------
    def test_ferramenta_lenta_nao_bloqueia_e_respeita_tentativas(self):
        chamadas = []

        def lenta(**kwargs):
            chamadas.append(1)
            time.sleep(60)  # mockado: nao dorme de verdade
            return {"status": "erro", "result": "timeout simulado"}

        self._registar("lenta", lenta)
        inicio = time.perf_counter()
        resultado = simple_task._executar_passo("lenta", {})
        decorrido = time.perf_counter() - inicio

        self.assertLess(decorrido, 2.0, "o teste dormiu de verdade (mock inefectivo)")
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["erro"], "timeout simulado")
        self.assertEqual(len(chamadas), 2)
        # 60 (da ferramenta) + 1 (retry) por tentativa
        self.assertEqual(self.dormidas, [60, 1, 60, 1])

    # -- sucesso -----------------------------------------------------------
    def test_sucesso_devolve_ok_true_sem_erro(self):
        chamadas = []

        def boa(**kwargs):
            chamadas.append(kwargs)
            return {"status": "ok", "result": "feito"}

        self._registar("boa", boa)
        resultado = simple_task._executar_passo("boa", {"x": 1})

        self._validar_forma(resultado)
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["resultado"], {"status": "ok", "result": "feito"})
        self.assertIsNone(resultado["erro"])
        self.assertEqual(chamadas, [{"x": 1}], "sucesso nao deve repetir")
        self.assertEqual(self.dormidas, [])

    def test_sucesso_com_resultado_nao_dict_ou_vazio(self):
        casos = [
            "texto simples", "", None, 0, -1, 3.14, True, [], {}, [1, 2],
            b"bytes", "\U0001F600 unicode",
        ]
        for valor in casos:
            with self.subTest(valor=repr(valor)):
                nome = f"retorna_{type(valor).__name__}"
                self._registar(nome, lambda valor=valor, **kw: valor)
                resultado = simple_task._executar_passo(nome, {})
                self._validar_forma(resultado)
                self.assertTrue(resultado["ok"])
                self.assertEqual(resultado["resultado"], valor)
                self.assertIsNone(resultado["erro"])

    def test_status_ok_mas_com_erro_no_dict_nao_conta_como_falha(self):
        """Contrato: so ``status == "erro"`` dispara retry/falha."""
        self._registar("meio_erro", lambda **kw: {"status": "ok", "erro": "aviso"})
        resultado = simple_task._executar_passo("meio_erro", {})
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["resultado"], {"status": "ok", "erro": "aviso"})

    def test_status_com_tipo_errado_nao_dispara_falha(self):
        self._registar("status_estranho", lambda **kw: {"status": "ERRO"})
        resultado = simple_task._executar_passo("status_estranho", {})
        self.assertTrue(resultado["ok"])

    # -- tentativas --------------------------------------------------------
    def test_numero_de_tentativas_e_respeitado(self):
        for tentativas, esperadas in ((1, 1), (2, 2), (3, 3), (5, 5)):
            with self.subTest(tentativas=tentativas):
                self.dormidas.clear()
                contador = {"n": 0}

                def conta(**kwargs):
                    contador["n"] += 1
                    raise RuntimeError("sempre")

                self._registar("conta", conta)
                resultado = simple_task._executar_passo("conta", {}, tentativas=tentativas)
                self.assertFalse(resultado["ok"])
                self.assertEqual(contador["n"], esperadas)
                self.assertEqual(len(self.dormidas), esperadas)

    def test_tentativas_com_tipo_invalido_levanta_type_error(self):
        """Caracterizacao: ``tentativas`` e um parametro interno (int).

        Tipos invalidos falham em ``range(1, tentativas + 1)``, ANTES de a
        ferramenta correr, e o TypeError propaga. Nao e alcancavel pelo
        planner, que chama sempre ``_executar_passo(ferramenta, args)`` com o
        default 2 — por isso nao e tratado como defeito.
        """
        chamadas = []

        def ok_fn(**kwargs):
            chamadas.append(kwargs)
            return {"status": "ok"}

        self._registar("ok_fn", ok_fn)
        for tentativas in ("2", 2.5, None, [2]):
            with self.subTest(tentativas=repr(tentativas)):
                with self.assertRaises(TypeError):
                    simple_task._executar_passo("ok_fn", {}, tentativas=tentativas)
        self.assertEqual(chamadas, [], "a ferramenta nao devia ter corrido")
        self.assertEqual(self.dormidas, [])

    @unittest.expectedFailure
    def test_tentativas_zero_deveria_devolver_erro_preenchido(self):
        """BUG: com tentativas <= 0 o retorno tem ``erro=None``.

        Contrato do projecto: quando a execucao falha, ``_executar_passo``
        devolve ``{"ok": False, "resultado": None, "erro": <mensagem>}``. Com
        ``tentativas=0`` o laco ``for tentativa in range(1, 1)`` nunca corre,
        ``ultimo_erro`` continua ``None`` e esse ``None`` e devolvido como erro
        (e depois guardado no historico da task e entregue a
        ``autonomy.recuperar``, que espera uma mensagem).

        Evidencia: ``_executar_passo("_ok", {}, tentativas=0)`` devolve
        ``{"ok": False, "resultado": None, "erro": None}``.

        Nao e alcancavel pelo ``executar_task`` (que usa o default 2), por isso
        a severidade e baixa.
        """
        self._registar("_ok", lambda **kw: {"status": "ok", "result": "x"})
        resultado = simple_task._executar_passo("_ok", {}, tentativas=0)
        self._validar_forma(resultado)
        self.assertFalse(resultado["ok"])
        self.assertIsNotNone(resultado["erro"], "erro devolvido como None")

    # -- efeitos colaterais ------------------------------------------------
    def test_nao_muta_o_registo_nem_os_args(self):
        self._registar("ok_fn", lambda **kw: {"status": "ok", "result": 1})
        antes = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        args = {"a": 1, "b": "x", "c": [1, 2]}
        copia = {"a": 1, "b": "x", "c": [1, 2]}

        resultado = simple_task._executar_passo("ok_fn", args)

        self.assertTrue(resultado["ok"])
        self.assertEqual(args, copia)
        self.assertEqual(dict(simple_task.FERRAMENTAS_DISPONIVEIS), antes)
        self.assertIs(simple_task.FERRAMENTAS_DISPONIVEIS["ok_fn"], antes["ok_fn"])

    def test_args_com_chaves_perigosas_chegam_intactos_a_ferramenta(self):
        recebido = {}

        def captura(**kwargs):
            recebido.update(kwargs)
            return {"status": "ok"}

        self._registar("captura", captura)
        args = {
            "caminho": "../../etc/passwd",
            "texto": "'; DROP TABLE tasks; --",
            "unicode": "a\u00e7\u00e3o \U0001F600",
            "vazio": "",
            "grande": "x" * 100000,
            "zero": 0,
            "nulo": None,
        }
        resultado = simple_task._executar_passo("captura", args)
        self.assertTrue(resultado["ok"])
        self.assertEqual(recebido, args)

    def test_dois_passos_seguidos_nao_acumulam_estado(self):
        modo = {"falhar": True}

        def alterna(**kwargs):
            if modo["falhar"]:
                return {"status": "erro", "result": "primeira falha"}
            return {"status": "ok", "result": "segunda ok"}

        self._registar("alterna", alterna)
        primeiro = simple_task._executar_passo("alterna", {})
        self.assertEqual(len(self.dormidas), 2, "primeiro passo: 2 tentativas")

        modo["falhar"] = False
        segundo = simple_task._executar_passo("alterna", {})

        self.assertFalse(primeiro["ok"])
        self.assertIsNone(primeiro["resultado"])
        self.assertEqual(primeiro["erro"], "primeira falha")
        self.assertTrue(segundo["ok"])
        self.assertEqual(segundo["resultado"], {"status": "ok", "result": "segunda ok"})
        self.assertIsNone(segundo["erro"])
        self.assertEqual(len(self.dormidas), 2, "o sucesso nao deve dormir")


if __name__ == "__main__":
    unittest.main(verbosity=2)
