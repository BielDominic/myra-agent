# -*- coding: utf-8 -*-
"""Testes severos do nucleo offline de ``tasks/simple_task.py``,
``computer/observer.py`` e ``tasks/cancel_state.py``.

Alvos cobertos:

* ``simple_task``: ``_extrair_json``, ``_formatar_resultado``,
  ``_formatar_historico``, ``_adicionar_observacao_ao_historico_str``,
  ``_deve_observar``, ``_observar``, ``_resposta``, ``_bloquear_acao``,
  ``_executar_passo`` (+ integracao minima de cancelamento/pausa com
  ``executar_task``);
* ``computer.observer``: ``_extrair_json`` e ``observar`` (com ``urllib``
  substituido por ``helpers.HTTPFalso`` / ``RespostaHTTPFalsa``);
* ``tasks.cancel_state``: marcar/resetar/consultar cancelamento e pausa.

Seguranca (obrigatoria):

* ``sem_rede()`` em todos os testes que poderiam abrir um socket (nada de
  Ollama :11434, backend :8000, visao :8081, IMAP/SMTP, Internet);
* ``helpers.CasoBase`` isola ``MYRA_TASK_DB`` / ``MYRA_BROWSER_BRIDGE_DB`` num
  diretorio temporario (nenhum banco do utilizador e' tocado);
* ``_executar_passo`` corre sempre com ferramentas FALSAS registadas em
  ``FERRAMENTAS_DISPONIVEIS`` (nunca chama browser, pyautogui, subprocess, etc.);
* ``time.sleep`` e' substituido nos caminhos de retry (os testes ficam rapidos
  e nao ha espera real).

Os testes marcados com ``@unittest.expectedFailure`` documentam bugs de
producao encontrados (prefixo ``BUG:`` no comentario) e NAO sao correcoes.
"""
from __future__ import annotations

import contextlib
import gc
import importlib
import io
import json
import math
import socket
import unittest
import urllib.error
import warnings
from unittest import mock

from tests import helpers
from tests.helpers import HTTPFalso, RespostaHTTPFalsa, sem_rede

from computer import observer as observer_mod
from tasks import cancel_state, simple_task as st


# ============================================================
# Apoio
# ============================================================

class CasoOffline(helpers.CasoBase):
    """``CasoBase`` + stdout silenciado.

    As funcoes de producao imprimem bastante (``[TASK] ...``). Redirecionar o
    stdout mantem a saida do unittest legivel e evita ``UnicodeEncodeError``
    quando o console esta em cp1252 e o teste usa emojis.
    """

    def setUp(self) -> None:
        super().setUp()
        self._stdout = io.StringIO()
        self._redir = contextlib.redirect_stdout(self._stdout)
        self._redir.__enter__()
        self.addCleanup(self._parar_stdout)

    def _parar_stdout(self) -> None:
        self._redir.__exit__(None, None, None)


class CasoCancelamento(CasoOffline):
    """Estado global de cancelamento/pausa sempre limpo antes e depois."""

    def setUp(self) -> None:
        super().setUp()
        cancel_state.resetar()
        cancel_state.resetar_pausa()

    def tearDown(self) -> None:
        cancel_state.resetar()
        cancel_state.resetar_pausa()
        super().tearDown()


def erro_http(codigo: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        observer_mod.OLLAMA_URL, codigo, f"erro HTTP {codigo}", None, io.BytesIO(b"")
    )


def resposta_chat(conteudo) -> RespostaHTTPFalsa:
    """Resposta no formato do /api/chat do Ollama."""
    return RespostaHTTPFalsa({"message": {"content": conteudo}, "done": True})


class RespostaQuebrada:
    """Resposta que rebenta ao ler o corpo (dentro do ``with``)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        raise OSError("ligacao caiu a meio da leitura")


class RespostaSemContexto:
    """Resposta sem suporte a context manager (urlopen devolve isto)."""

    def read(self):
        return b"{}"


# ============================================================
# 1. simple_task._extrair_json
# ============================================================

class ExtrairJsonSimpleTaskTestCase(CasoOffline):
    """``_extrair_json`` tem de aguentar texto degenerado sem levantar."""

    def test_entradas_degeneradas_devolvem_none_sem_levantar(self):
        casos = [
            "", " ", "\n\t\r", "{", "}", "}{", "[1,2", "[]]", "{{}}",
            "texto sem json", "```", "```json", "```json\n```", "```\n```",
            "[1,2,", "nada de util aqui", "resultado: (sem json)",
            "\U0001f680 \U0001f4a5", "<html><body>erro 502</body></html>",
        ]
        with sem_rede():
            for caso in casos:
                with self.subTest(caso=caso):
                    self.assertIsNone(st._extrair_json(caso))

    def test_json_valido_simples(self):
        casos = [
            ('{"a": 1}', {"a": 1}),
            ("{}", {}),
            ("[]", []),
            ("[1, 2, 3]", [1, 2, 3]),
            ('{"acao": "chamar", "ferramenta": "x", "args": {"n": 2}}',
             {"acao": "chamar", "ferramenta": "x", "args": {"n": 2}}),
            ('{"a": null, "b": true, "c": false, "d": 1.5}',
             {"a": None, "b": True, "c": False, "d": 1.5}),
            ('"\U0001f680 texto"', "\U0001f680 texto"),
        ]
        with sem_rede():
            for texto, esperado in casos:
                with self.subTest(texto=texto):
                    self.assertEqual(st._extrair_json(texto), esperado)

    def test_escalares_json(self):
        with sem_rede():
            self.assertIs(st._extrair_json("true"), True)
            self.assertIs(st._extrair_json("false"), False)
            self.assertIsNone(st._extrair_json("null"))
            self.assertEqual(st._extrair_json("123"), 123)
            self.assertEqual(st._extrair_json('"texto puro"'), "texto puro")

    def test_json_nao_padrao_nan_e_infinity_sao_aceites(self):
        """``json.loads`` do Python aceita NaN/Infinity (nao e' JSON estrito)."""
        with sem_rede():
            nan = st._extrair_json("NaN")
            self.assertIsInstance(nan, float)
            self.assertTrue(math.isnan(nan))
            self.assertEqual(st._extrair_json("Infinity"), float("inf"))

    def test_json_dentro_de_fences_markdown(self):
        casos = [
            '```json\n{"a": 1}\n```',
            '```\n{"a": 1}\n```',
            '```JSON\n{"a": 1}\n```',
            '```json\n[1, 2]\n```',
            '```json\n{"a": {"b": [1, 2]}}\n```',
        ]
        with sem_rede():
            for caso in casos:
                with self.subTest(caso=caso):
                    resultado = st._extrair_json(caso)
                    self.assertIsInstance(resultado, (dict, list), repr(resultado))

    def test_json_com_texto_extra_antes_e_depois(self):
        with sem_rede():
            self.assertEqual(
                st._extrair_json('Claro! Aqui esta:\n{"a": 1}\nEspero ter ajudado.'),
                {"a": 1},
            )
            self.assertEqual(st._extrair_json('bla {"a": 1} bla'), {"a": 1})
            self.assertEqual(
                st._extrair_json('```json\n{"a": 1}\n``` e depois {"b": 2}'), {"a": 1}
            )
            self.assertEqual(st._extrair_json('\ufeff{"a": 1}'), {"a": 1})

    def test_json_com_chaves_duplicadas_fica_com_a_ultima(self):
        with sem_rede():
            self.assertEqual(st._extrair_json('{"a": 1, "a": 2, "a": 3}'), {"a": 3})

    def test_chaves_e_strings_com_caracteres_perigosos(self):
        with sem_rede():
            self.assertEqual(st._extrair_json('{"a": "}"}'), {"a": "}"})
            self.assertEqual(
                st._extrair_json('{"motivo": "use { e } e ``` dentro"}'),
                {"motivo": "use { e } e ``` dentro"},
            )
            self.assertEqual(
                st._extrair_json('{"cmd": "rm -rf / && $(whoami)"}'),
                {"cmd": "rm -rf / && $(whoami)"},
            )
            self.assertEqual(st._extrair_json('{"a": "linha\\nquebrada"}'),
                             {"a": "linha\nquebrada"})

    def test_dois_objetos_seguidos_devolve_none(self):
        """Limitacao documentada: o fallback usa o primeiro ``{`` e o ultimo ``}``."""
        with sem_rede():
            self.assertIsNone(st._extrair_json('{"a": 1}{"b": 2}'))
            self.assertIsNone(st._extrair_json('aviso {nao json} depois {"a": 1}'))

    def test_aninhamento_profundo_balanceado(self):
        esperado = {"n": None}
        no = esperado
        for _ in range(200):
            no["n"] = {"n": None}
            no = no["n"]
        with sem_rede():
            self.assertEqual(st._extrair_json(json.dumps(esperado)), esperado)

    def test_aninhamento_desbalanceado_nao_propaga(self):
        with sem_rede():
            self.assertIsNone(st._extrair_json('{"n": ' + "[" * 3000))
            self.assertIsNone(st._extrair_json('{"n": ' + "[" * 3000 + "]" * 2999))

    def test_json_enorme(self):
        grande = {"k": list(range(50000)), "texto": "x" * 200000}
        with sem_rede():
            resultado = st._extrair_json(json.dumps(grande))
        self.assertEqual(len(resultado["k"]), 50000)
        self.assertEqual(len(resultado["texto"]), 200000)

    def test_bytes_sao_aceites_pelo_json_loads(self):
        with sem_rede():
            self.assertEqual(st._extrair_json(b'{"a": 1}'), {"a": 1})

    def test_tipos_errados_propagam_type_error_documentado(self):
        """NOTA: contrato interno e' ``str``; tipos errados nao sao tolerados.

        Isto esta reportado nas notas do relatorio: ``_extrair_json(None)`` falha
        no ``re.search`` (o ``except`` cobre apenas o ``json.loads``).
        """
        with sem_rede():
            for valor in (None, 123, ["{}"], {"a": 1}, 4.5):
                with self.subTest(valor=repr(valor)):
                    with self.assertRaises(TypeError):
                        st._extrair_json(valor)


# ============================================================
# 2. computer.observer._extrair_json
# ============================================================

class ExtrairJsonObserverTestCase(CasoOffline):
    """Variante do observer: so extrai OBJETOS JSON (nunca listas/escalares)."""

    def test_entradas_falsas_devolvem_none(self):
        with sem_rede():
            for valor in ["", "   ", None, 0, False, [], {}, "sem json", "```",
                          "```json\n```", "null", "[1, 2]", "123", "texto { sem fim"]:
                with self.subTest(valor=repr(valor)):
                    self.assertIsNone(observer_mod._extrair_json(valor))

    def test_objeto_simples_e_aninhado(self):
        with sem_rede():
            self.assertEqual(observer_mod._extrair_json('{"a": 1}'), {"a": 1})
            self.assertEqual(
                observer_mod._extrair_json('{"a": {"b": {"c": [1, {"d": 2}]}}}'),
                {"a": {"b": {"c": [1, {"d": 2}]}}},
            )

    def test_objeto_vazio_fence_incluido(self):
        """``{}`` devolve dict vazio (falsy) - quem chama trata como "sem dados"."""
        with sem_rede():
            self.assertEqual(observer_mod._extrair_json("{}"), {})
            self.assertEqual(observer_mod._extrair_json("```json\n{}\n```"), {})
            self.assertIsNotNone(observer_mod._extrair_json("{}"))

    def test_fences_markdown_variados(self):
        casos = [
            '```json\n{"a": 1}\n```',
            '```\n{"a": 1}\n```',
            '```json\n{"a": 1}\n```   ',
            '```json\n{"a": 1}```',
            '```json\n{"a": 1}',
            'Aqui:\n```json\n{"a": 1}\n```\nFim.',
        ]
        with sem_rede():
            for caso in casos:
                with self.subTest(caso=caso):
                    self.assertEqual(observer_mod._extrair_json(caso), {"a": 1})

    def test_texto_extra_e_caracteres_perigosos(self):
        with sem_rede():
            self.assertEqual(observer_mod._extrair_json('bla {"a": 1} fim'), {"a": 1})
            self.assertEqual(observer_mod._extrair_json('{"a": "}"}'), {"a": "}"})
            self.assertEqual(
                observer_mod._extrair_json('{"motivo": "tem ``` e { dentro"}'),
                {"motivo": "tem ``` e { dentro"},
            )
            self.assertEqual(
                observer_mod._extrair_json('ruido {"sucesso": true, "motivo": "\U0001f680 ok"}'),
                {"sucesso": True, "motivo": "\U0001f680 ok"},
            )

    def test_varios_objetos_devolve_none(self):
        with sem_rede():
            self.assertIsNone(observer_mod._extrair_json('{"a": 1}\n{"b": 2}'))
            self.assertIsNone(observer_mod._extrair_json('{"a": 1} lixo {"b": 2}'))

    def test_aninhamento_profundo_e_desbalanceado(self):
        with sem_rede():
            self.assertEqual(
                observer_mod._extrair_json('{"a": ' * 50 + "1" + "}" * 50),
                json.loads('{"a": ' * 50 + "1" + "}" * 50),
            )
            self.assertIsNone(observer_mod._extrair_json('{"n": ' + "[" * 3000))

    def test_tipos_errados_propagam_attribute_error_documentado(self):
        """NOTA: contrato interno e' ``str`` (so valores falsy sao tolerados)."""
        with sem_rede():
            for valor in (123, 4.5, True):
                with self.subTest(valor=repr(valor)):
                    with self.assertRaises(AttributeError):
                        observer_mod._extrair_json(valor)


# ============================================================
# 3. simple_task._formatar_resultado
# ============================================================

class FormatarResultadoTestCase(CasoOffline):
    """Formatacao de resultados do navegador (texto/tabelas/links/botoes/inputs)."""

    def test_resultado_vazio_devolve_string_vazia(self):
        with sem_rede():
            self.assertEqual(st._formatar_resultado({}), "")
            self.assertIsInstance(st._formatar_resultado({}), str)

    def test_campos_isolados(self):
        with sem_rede():
            self.assertEqual(st._formatar_resultado({"title": "Pagina"}), "Title: Pagina")
            self.assertEqual(st._formatar_resultado({"url": "http://x/y"}), "URL: http://x/y")
            self.assertIn("Texto visivel:\nconteudo",
                          st._formatar_resultado({"text": "conteudo"}))
            self.assertEqual(st._formatar_resultado({"buttons": ["A", "B"]}),
                             "\nBotoes: A, B")
            self.assertIn("Campos: 3 inputs",
                          st._formatar_resultado({"inputs": [1, 2, 3]}))
            self.assertIn("=== LINKS ===", st._formatar_resultado(
                {"links": [{"text": "t", "href": "h"}]}))

    def test_titulo_e_texto_nao_string_nao_propagam(self):
        with sem_rede():
            self.assertEqual(st._formatar_resultado({"title": 5}), "Title: 5")
            self.assertEqual(st._formatar_resultado({"title": None}), "")
            self.assertIn("{'a': 1}", st._formatar_resultado({"text": {"a": 1}}))
            self.assertIn("b'bytes'", st._formatar_resultado({"text": b"bytes"}))

    def test_texto_e_truncado_em_2500_caracteres(self):
        with sem_rede():
            saida = st._formatar_resultado({"text": "Z" * 6000})
        self.assertEqual(saida.count("Z"), 2500)
        self.assertNotIn("Z" * 2501, saida)

    def test_tabela_com_linhas_de_comprimentos_diferentes(self):
        resultado = {"tables": [{
            "caption": "Vendas",
            "rows": [
                ["nome", "total"],
                ["so_um"],
                ["a", "b", "c"],
                [],
            ],
        }]}
        with sem_rede():
            saida = st._formatar_resultado(resultado)
        self.assertIn("--- Vendas ---", saida)
        self.assertIn("nome: total", saida)
        self.assertIn("so_um", saida)
        self.assertIn("a | b | c", saida)
        self.assertNotIn("\n\n\n", saida)

    def test_celulas_none_e_vazias(self):
        resultado = {"tables": [{"caption": "c", "rows": [
            [None, "so_valor"],
            [None, None],
            ["", "vazio_a_esquerda"],
            [1, 2],
            ["\U0001f680", "emoji"],
        ]}]}
        with sem_rede():
            saida = st._formatar_resultado(resultado)
        self.assertIn("so_valor", saida)
        self.assertIn(": vazio_a_esquerda", saida)
        self.assertIn("1: 2", saida)
        self.assertIn("\U0001f680: emoji", saida)
        # a linha so com None nao pode gerar linha nenhuma
        self.assertNotIn("None: None", saida)

    def test_caption_ausente_vazia_ou_nao_string(self):
        with sem_rede():
            self.assertIn("--- tabela 1 ---",
                          st._formatar_resultado({"tables": [{"rows": [["a", "b"]]}]}))
            self.assertIn("--- tabela 1 ---",
                          st._formatar_resultado({"tables": [{"caption": "", "rows": [["a", "b"]]}]}))
            self.assertIn("--- tabela 1 ---",
                          st._formatar_resultado({"tables": [{"caption": None, "rows": [["a", "b"]]}]}))
            self.assertIn("--- 7 ---",
                          st._formatar_resultado({"tables": [{"caption": 7, "rows": [["a", "b"]]}]}))

    def test_tabela_sem_rows_nao_propaga(self):
        with sem_rede():
            saida = st._formatar_resultado({"tables": [{"caption": "so_caption"}]})
        self.assertIn("so_caption", saida)

    def test_truncagem_a_3_tabelas_e_30_linhas(self):
        tabelas = [
            {"caption": f"cap{i}", "rows": [[f"c{i}-{j}Z", "v"] for j in range(40)]}
            for i in range(5)
        ]
        with sem_rede():
            saida = st._formatar_resultado({"tables": tabelas})
        self.assertIn("cap2", saida)
        self.assertNotIn("cap3", saida)
        self.assertIn("c0-29Z: v", saida)
        self.assertNotIn("c0-30Z", saida)

    def test_tabela_de_10000_linhas_e_10000_tabelas(self):
        with sem_rede():
            uma = st._formatar_resultado(
                {"tables": [{"caption": "grande", "rows": [[f"L{j}K", "v"] for j in range(10000)]}]}
            )
            muitas = st._formatar_resultado(
                {"tables": [{"caption": f"T{i}", "rows": [["a", "b"]]} for i in range(10000)]}
            )
        self.assertIn("L29K: v", uma)
        self.assertNotIn("L30K", uma)
        self.assertIn("T2", muitas)
        self.assertNotIn("T3", muitas)

    def test_links_limitados_a_10(self):
        links = [{"text": f"lig{i}", "href": f"http://h/{i}"} for i in range(15)]
        with sem_rede():
            saida = st._formatar_resultado({"links": links})
        self.assertIn("lig9: http://h/9", saida)
        self.assertNotIn("lig10", saida)

    def test_links_com_campos_em_falta_nao_propaga(self):
        with sem_rede():
            saida = st._formatar_resultado({"links": [{"href": "http://x"}, {"text": "so_texto"}]})
        self.assertIn(": http://x", saida)
        self.assertIn("so_texto: ", saida)

    def test_botoes_limitados_a_15(self):
        with sem_rede():
            saida = st._formatar_resultado({"buttons": [f"bt{i}" for i in range(20)]})
        self.assertIn("bt14", saida)
        self.assertNotIn("bt15", saida)

    def test_resultado_com_tipos_errados_documentado(self):
        """Contrato anotado: ``res`` e' ``dict`` (outros tipos nao sao suportados)."""
        with sem_rede():
            for valor in (None, [], "texto", 5):
                with self.subTest(valor=repr(valor)):
                    with self.assertRaises(AttributeError):
                        st._formatar_resultado(valor)

    # ------------------------------------------------------------
    # BUG: estruturas malformadas (dados vindos do Browser Bridge) derrubam a
    # formatacao, em vez de degradarem para texto/linha vazia.
    # ------------------------------------------------------------

    @unittest.expectedFailure
    def test_tables_com_item_nao_dict_nao_propaga(self):
        # BUG: res["tables"] com item None/str -> AttributeError em ``tabela.get``.
        # Evidencia: _formatar_resultado({"tables": [None]}) levanta
        # "AttributeError: 'NoneType' object has no attribute 'get'".
        with sem_rede():
            saida = st._formatar_resultado({"tables": [None, "linha_solta"]})
        self.assertIsInstance(saida, str)

    @unittest.expectedFailure
    def test_tables_com_linha_nao_iteravel_nao_propaga(self):
        # BUG: rows com item nao iteravel (None/int) -> TypeError no ``for row in``.
        # Evidencia: _formatar_resultado({"tables":[{"rows":[5]}]}) levanta
        # "TypeError: 'int' object is not iterable".
        with sem_rede():
            saida = st._formatar_resultado({"tables": [{"caption": "c", "rows": [None, 5]}]})
        self.assertIsInstance(saida, str)

    @unittest.expectedFailure
    def test_links_com_item_nao_dict_nao_propaga(self):
        # BUG: res["links"] com item str -> AttributeError em ``link.get``.
        # Evidencia: _formatar_resultado({"links": ["http://x"]}) levanta
        # "AttributeError: 'str' object has no attribute 'get'".
        with sem_rede():
            saida = st._formatar_resultado({"links": ["http://x", None]})
        self.assertIsInstance(saida, str)

    @unittest.expectedFailure
    def test_buttons_e_inputs_escalares_nao_propagam(self):
        # BUG: buttons/inputs escalares -> TypeError (nao indexavel / sem len).
        # Evidencia: buttons=5 -> "TypeError: 'int' object is not subscriptable";
        # inputs=5 -> "TypeError: object of type 'int' has no len()".
        with sem_rede():
            self.assertIsInstance(st._formatar_resultado({"buttons": 5}), str)
            self.assertIsInstance(st._formatar_resultado({"inputs": 5}), str)


# ============================================================
# 4. simple_task._formatar_historico
# ============================================================

class FormatarHistoricoTestCase(CasoOffline):
    """Historico textual: entradas ok/erro, truncagem e tipos degenerados."""

    def _passo(self, **extra):
        base = {
            "passo": 1, "ferramenta": "write_file", "args": {"caminho": "a.txt"},
            "ok": True, "resultado": "feito", "erro": None,
        }
        base.update(extra)
        return base

    def test_historico_vazio_ou_none(self):
        with sem_rede():
            self.assertEqual(st._formatar_historico([]), "(nenhum passo executado ainda)")
            self.assertEqual(st._formatar_historico(None), "(nenhum passo executado ainda)")

    def test_passo_ok_e_passo_com_erro(self):
        historico = [
            self._passo(),
            self._passo(passo=2, ok=False, resultado=None, erro="ValueError: explodiu"),
        ]
        with sem_rede():
            saida = st._formatar_historico(historico)
        self.assertIn("--- PASSO 1 ---", saida)
        self.assertIn("Ferramenta: write_file", saida)
        self.assertIn('Args: {"caminho": "a.txt"}', saida)
        self.assertIn("Resultado: feito", saida)
        self.assertIn("--- PASSO 2 ---", saida)
        self.assertIn("ERRO: ValueError: explodiu", saida)

    def test_erro_none_aparece_como_none(self):
        with sem_rede():
            saida = st._formatar_historico([self._passo(ok=False, resultado=None, erro=None)])
        self.assertIn("ERRO: None", saida)

    def test_resultado_dict_com_result_usa_o_campo_result(self):
        with sem_rede():
            saida = st._formatar_historico(
                [self._passo(resultado={"status": "ok", "result": "escrevi o ficheiro"})]
            )
        self.assertIn("Resultado: escrevi o ficheiro", saida)

    def test_resultado_dict_com_text_usa_formatar_resultado(self):
        with sem_rede():
            saida = st._formatar_historico(
                [self._passo(resultado={"title": "T", "text": "corpo da pagina"})]
            )
        self.assertIn("Title: T", saida)
        self.assertIn("Texto visivel:", saida)

    def test_resultado_dict_com_tables_usa_formatar_resultado(self):
        with sem_rede():
            saida = st._formatar_historico(
                [self._passo(resultado={"tables": [{"caption": "c", "rows": [["a", "b"]]}]})]
            )
        self.assertIn("=== TABELAS ===", saida)

    def test_resultado_dict_sem_text_nem_tables_vira_json(self):
        with sem_rede():
            saida = st._formatar_historico([self._passo(resultado={"a": 1, "b": "x"})])
        self.assertIn('{"a": 1, "b": "x"}', saida)

    def test_resultado_nao_dict_vira_str(self):
        with sem_rede():
            for valor, esperado in [(42, "Resultado: 42"), (None, "Resultado: None"),
                                    ([1, 2], "Resultado: [1, 2]"),
                                    ("texto", "Resultado: texto")]:
                with self.subTest(valor=repr(valor)):
                    self.assertIn(esperado, st._formatar_historico([self._passo(resultado=valor)]))

    def test_unicode_e_emojis_preservados(self):
        with sem_rede():
            saida = st._formatar_historico(
                [self._passo(args={"nome": "\U0001f680"}, resultado="olá ção \U0001f4a5")]
            )
        self.assertIn("\U0001f680", saida)
        self.assertIn("olá ção \U0001f4a5", saida)

    def test_truncagem_em_5000_caracteres(self):
        with sem_rede():
            limite = st._formatar_historico([self._passo(resultado="Q" * 5001)])
            exato = st._formatar_historico([self._passo(resultado="Q" * 5000)])
        self.assertIn("Q" * 5000 + "...(truncado)", limite)
        self.assertEqual(limite.count("Q"), 5000)
        self.assertNotIn("...(truncado)", exato)

    def test_texto_grande_do_browser_e_truncado_antes_do_limite_do_historico(self):
        """``_formatar_resultado`` corta em 2500, logo nao sobra para os 5000."""
        with sem_rede():
            saida = st._formatar_historico([self._passo(resultado={"text": "Z" * 6000})])
        self.assertNotIn("...(truncado)", saida)
        self.assertEqual(saida.count("Z"), 2500)

    def test_varios_passos_ficam_todos_no_historico(self):
        historico = [self._passo(passo=i, resultado=f"r{i}") for i in range(1, 6)]
        with sem_rede():
            saida = st._formatar_historico(historico)
        for i in range(1, 6):
            self.assertIn(f"--- PASSO {i} ---", saida)
            self.assertIn(f"Resultado: r{i}", saida)

    # ------------------------------------------------------------
    # BUG: valores nao serializaveis em resultado/args derrubam o historico.
    # A causa e' ``json.dumps(res, ...)`` avaliado ansiosamente como argumento
    # por omissao de ``res.get("result", ...)``.
    # ------------------------------------------------------------

    @unittest.expectedFailure
    def test_resultado_dict_com_bytes_nao_propaga(self):
        # BUG: mesmo com "result" textual, o json.dumps(res) ansioso rebenta.
        # Evidencia: _formatar_historico([{..., "resultado": {"result": "ok",
        # "raw": b"\x00\x01"}}]) levanta
        # "TypeError: Object of type bytes is not JSON serializable".
        with sem_rede():
            saida = st._formatar_historico(
                [self._passo(resultado={"result": "ok", "raw": b"\x00\x01"})]
            )
        self.assertIn("Resultado: ok", saida)

    @unittest.expectedFailure
    def test_args_com_objeto_nao_serializavel_nao_propaga(self):
        # BUG: json.dumps(h["args"]) sem tratamento de excecao.
        # Evidencia: args={"obj": object()} levanta
        # "TypeError: Object of type object is not JSON serializable".
        with sem_rede():
            saida = st._formatar_historico([self._passo(args={"obj": object()})])
        self.assertIsInstance(saida, str)


# ============================================================
# 5. simple_task._adicionar_observacao_ao_historico_str
# ============================================================

class ObservacaoNoHistoricoTestCase(CasoOffline):
    """Bloco de observacoes/verificacoes/recuperacoes acrescentado ao historico."""

    def _passo(self, **extra):
        base = {
            "passo": 3, "ferramenta": "vision_click", "args": {"descricao": "Entrar"},
            "ok": True, "resultado": "cliquei", "erro": None,
        }
        base.update(extra)
        return base

    def test_historico_vazio_mantem_a_base(self):
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str([])
        self.assertEqual(saida, "(nenhum passo executado ainda)")
        self.assertNotIn("OBSERVACOES", saida)

    def test_observacao_ok_e_acrescentada(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": False, "motivo": "clicou"}
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str([self._passo(observacao=obs)])
        self.assertIn("OBSERVACOES / VERIFICACOES:", saida)
        self.assertIn(
            "Passo 3: obs -> sucesso=True objetivo_atingido=False motivo=clicou", saida
        )

    def test_observacao_com_status_diferente_de_ok_e_ignorada(self):
        with sem_rede():
            for obs in ({"status": "erro", "sucesso": True}, {"status": "OK"}, {},
                        None, {}, {"status": "ok"}):
                with self.subTest(obs=repr(obs)):
                    saida = st._adicionar_observacao_ao_historico_str(
                        [self._passo(observacao=obs)]
                    )
                    if obs == {"status": "ok"}:
                        self.assertIn("obs -> sucesso=None", saida)
                    else:
                        self.assertNotIn("OBSERVACOES", saida)

    def test_motivo_da_observacao_truncado_em_150(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "M" * 500}
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str([self._passo(observacao=obs)])
        self.assertIn("M" * 150, saida)
        self.assertNotIn("M" * 151, saida)

    def test_verificacao_e_recuperacao(self):
        ver = {"atingido": False, "confianca": "alta", "motivo": "nao atingiu"}
        rec = {"recuperar": True, "desistir": False, "motivo": "tentar outro caminho"}
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str(
                [self._passo(verificacao=ver, recuperacao=rec)]
            )
        self.assertIn("verificacao -> atingido=False confianca=alta motivo=nao atingiu", saida)
        self.assertIn("recuperacao -> recuperar=True desistir=False motivo=tentar outro caminho", saida)

    def test_verificacao_ou_recuperacao_vazias_sao_ignoradas(self):
        with sem_rede():
            for campo in ({"verificacao": {}}, {"recuperacao": {}}, {"verificacao": None},
                          {"recuperacao": None}):
                with self.subTest(campo=repr(campo)):
                    saida = st._adicionar_observacao_ao_historico_str([self._passo(**campo)])
                    self.assertNotIn("OBSERVACOES", saida)

    def test_campos_em_falta_nao_propagam(self):
        entrada = {"passo": 9, "ferramenta": "f", "args": {}, "ok": True,
                   "resultado": "r", "erro": None,
                   "observacao": {"status": "ok"}, "verificacao": {"atingido": True},
                   "recuperacao": {"recuperar": False}}
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str([entrada])
        self.assertIn("Passo 9: obs ->", saida)
        self.assertIn("motivo=", saida)

    def test_o_bloco_de_observacoes_vem_depois_do_historico(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "feito"}
        with sem_rede():
            saida = st._adicionar_observacao_ao_historico_str([self._passo(observacao=obs)])
        self.assertLess(saida.index("--- PASSO 3 ---"), saida.index("OBSERVACOES"))


# ============================================================
# 6. simple_task._deve_observar / _observar
# ============================================================

class DeveObservarTestCase(CasoOffline):

    def test_todas_as_ferramentas_declaradas_sao_observaveis(self):
        with sem_rede():
            for nome in st.FERRAMENTAS_OBSERVAVEIS:
                with self.subTest(nome=nome):
                    self.assertTrue(st._deve_observar(nome))

    def test_ferramentas_de_leitura_nao_sao_observaveis(self):
        nao_observaveis = [
            "read_file", "list_dir", "browser_read_page", "browser_read_active_tab",
            "browser_get_tabs", "web_search", "youtube_search", "vision_locate_errado",
        ]
        with sem_rede():
            for nome in nao_observaveis:
                with self.subTest(nome=nome):
                    self.assertFalse(st._deve_observar(nome))

    def test_nomes_invalidos_nao_propagam(self):
        with sem_rede():
            for valor in ["", " ", "VISION_CLICK", " vision_click", "vision_click ",
                          "vision_click\n", None, 123, 0, True]:
                with self.subTest(valor=repr(valor)):
                    self.assertFalse(st._deve_observar(valor))


class ObservarSimpleTaskTestCase(CasoOffline):

    def test_ferramenta_nao_observavel_nao_chama_o_observer(self):
        with mock.patch("computer.observer.observar") as falso, sem_rede():
            resultado = st._observar("objetivo", "read_file", {"caminho": "a"}, "conteudo", None)
        self.assertIsNone(resultado)
        falso.assert_not_called()

    def test_payload_enviado_ao_observer(self):
        observado = {"status": "ok", "sucesso": True, "objetivo_atingido": False, "motivo": "m"}
        with mock.patch("computer.observer.observar", return_value=observado) as falso, sem_rede():
            resultado = st._observar(
                "objetivo X", "write_file", {"caminho": "a.txt"}, {"status": "ok"}, None
            )
        self.assertEqual(resultado, observado)
        falso.assert_called_once_with("objetivo X", {
            "ferramenta": "write_file",
            "args": {"caminho": "a.txt"},
            "resultado": {"status": "ok"},
            "erro": None,
        })

    def test_resultado_nao_serializavel_e_passado_intacto(self):
        payload = b"\x00\xff"
        with mock.patch("computer.observer.observar", return_value={"status": "ok"}) as falso, sem_rede():
            st._observar("obj", "delete_file", {"p": "a"}, payload, "erro X")
        self.assertIs(falso.call_args[0][1]["resultado"], payload)
        self.assertEqual(falso.call_args[0][1]["erro"], "erro X")

    def test_status_de_erro_do_observer_devolve_none(self):
        with mock.patch("computer.observer.observar",
                        return_value={"status": "erro", "result": "LLM caiu"}), sem_rede():
            self.assertIsNone(st._observar("obj", "write_file", {}, "r", None))

    def test_observer_que_levanta_nao_propaga(self):
        erros = [RuntimeError("caiu"), ValueError("valor"), KeyError("k"),
                 TypeError("tipo"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"),
                 OSError("rede"), RecursionError("fundo")]
        for erro in erros:
            with self.subTest(erro=type(erro).__name__):
                with mock.patch("computer.observer.observar", side_effect=erro), sem_rede():
                    self.assertIsNone(st._observar("obj", "write_file", {}, "r", None))

    def test_observer_devolvendo_tipos_estranhos_devolve_none(self):
        with sem_rede():
            for valor in (None, "texto", 42, ["lista"]):
                with self.subTest(valor=repr(valor)):
                    with mock.patch("computer.observer.observar", return_value=valor):
                        self.assertIsNone(st._observar("obj", "write_file", {}, "r", None))

    def test_observer_real_sem_rede_devolve_none_sem_propagar(self):
        """``observar`` real, com a rede bloqueada: erro estruturado -> None."""
        with sem_rede():
            self.assertIsNone(st._observar("objetivo", "write_file", {"p": "a"}, "r", None))


# ============================================================
# 7. simple_task._executar_passo
# ============================================================

class ExecutarPassoTestCase(CasoOffline):
    """Execucao de ferramentas: retry, erros estruturados e tipos errados."""

    NOME_DESCONHECIDO = "ferramenta_falsa_nao_registada_xyz"

    def setUp(self) -> None:
        super().setUp()
        self._sleep = mock.patch("tasks.simple_task.time.sleep")
        self._sleep.start()
        self.addCleanup(mock.patch.stopall)

    def _com(self, **ferramentas):
        """Registo isolado: o dicionario real de ferramentas e' substituido."""
        return mock.patch.dict(st.FERRAMENTAS_DISPONIVEIS, ferramentas, clear=True)

    def test_ferramenta_desconhecida_devolve_erro_estruturado(self):
        with self._com(), sem_rede():
            resultado = st._executar_passo(self.NOME_DESCONHECIDO, {"a": 1})
        self.assertEqual(resultado, {
            "ok": False, "resultado": None,
            "erro": f"ferramenta desconhecida: {self.NOME_DESCONHECIDO}",
        })

    def test_sucesso_passa_kwargs_e_devolve_o_mesmo_objeto(self):
        recebido = {}
        esperado = {"status": "ok", "result": "feito"}

        def ferramenta(**kwargs):
            recebido.update(kwargs)
            return esperado

        with self._com(minha_ferramenta=ferramenta), sem_rede():
            resultado = st._executar_passo("minha_ferramenta", {"a": 1, "b": "\U0001f680"})
        self.assertEqual(recebido, {"a": 1, "b": "\U0001f680"})
        self.assertEqual(resultado, {"ok": True, "resultado": esperado, "erro": None})
        self.assertIs(resultado["resultado"], esperado)

    def test_unicode_e_emojis_chegam_a_ferramenta(self):
        def ferramenta(texto):
            return {"status": "ok", "result": texto}

        with self._com(eco=ferramenta), sem_rede():
            resultado = st._executar_passo("eco", {"texto": "olá ção \U0001f4a5 \u4e2d\u6587"})
        self.assertEqual(resultado["resultado"]["result"], "olá ção \U0001f4a5 \u4e2d\u6587")

    def test_args_nao_sao_mutados(self):
        def ferramenta(**kwargs):
            return kwargs

        args = {"a": 1}
        with self._com(copia=ferramenta), sem_rede():
            st._executar_passo("copia", args)
        self.assertEqual(args, {"a": 1})

    def test_erro_estruturado_da_ferramenta_tenta_de_novo(self):
        chamadas = []

        def ferramenta(**kwargs):
            chamadas.append(kwargs)
            return {"status": "erro", "result": "falhou ao escrever"}

        with self._com(quebrada=ferramenta), sem_rede():
            resultado = st._executar_passo("quebrada", {})
        self.assertEqual(resultado, {"ok": False, "resultado": None, "erro": "falhou ao escrever"})
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(st.time.sleep.call_count, 2)

    def test_erro_sem_campo_result_usa_mensagem_padrao(self):
        with self._com(sem_result=lambda **k: {"status": "erro"}), sem_rede():
            resultado = st._executar_passo("sem_result", {})
        self.assertEqual(resultado["erro"], "erro desconhecido")

    def test_erro_com_result_nao_string_e_devolvido_tal_e_qual(self):
        with self._com(codigo=lambda **k: {"status": "erro", "result": 500}), sem_rede():
            resultado = st._executar_passo("codigo", {})
        self.assertEqual(resultado["erro"], 500)

    def test_excecao_da_ferramenta_vira_erro_estruturado(self):
        def explode():
            raise ValueError("explodiu")

        with self._com(explode=explode), sem_rede():
            resultado = st._executar_passo("explode", {})
        self.assertEqual(resultado["ok"], False)
        self.assertEqual(resultado["resultado"], None)
        self.assertEqual(resultado["erro"], "ValueError: explodiu")

    def test_timeout_e_connection_error_sao_apanhados(self):
        casos = [socket.timeout("timed out"), TimeoutError("demorou"),
                 ConnectionRefusedError("recusado"), OSError("sem rota")]
        for erro in casos:
            with self.subTest(erro=type(erro).__name__):
                with self._com(cai=lambda e=erro, **k: (_ for _ in ()).throw(e)), sem_rede():
                    resultado = st._executar_passo("cai", {})
                self.assertFalse(resultado["ok"])
                self.assertTrue(str(resultado["erro"]).startswith(type(erro).__name__))
                self.assertIsNone(resultado["resultado"])

    def test_primeira_tentativa_falha_e_a_segunda_funciona(self):
        tentativas = []

        def instavel(**kwargs):
            tentativas.append(kwargs)
            if len(tentativas) == 1:
                raise RuntimeError("primeira falhou")
            return {"status": "ok", "result": "segunda ok"}

        with self._com(instavel=instavel), sem_rede():
            resultado = st._executar_passo("instavel", {})
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["resultado"]["result"], "segunda ok")
        self.assertEqual(len(tentativas), 2)
        self.assertEqual(st.time.sleep.call_count, 1)

    def test_tentativas_configuraveis(self):
        chamadas = []

        def sempre_erro(**kwargs):
            chamadas.append(1)
            return {"status": "erro", "result": "nunca da certo"}

        with self._com(sempre_erro=sempre_erro), sem_rede():
            st._executar_passo("sempre_erro", {}, tentativas=1)
            self.assertEqual(len(chamadas), 1)
            st._executar_passo("sempre_erro", {}, tentativas=3)
            self.assertEqual(len(chamadas), 4)

    def test_tentativas_zero_ou_negativa_nao_chama_nada(self):
        with self._com(nunca=lambda **k: {"status": "ok"}), sem_rede():
            for valor in (0, -1):
                with self.subTest(tentativas=valor):
                    resultado = st._executar_passo("nunca", {}, tentativas=valor)
                    self.assertEqual(resultado, {"ok": False, "resultado": None, "erro": None})

    def test_tentativas_zero_nao_chama_a_ferramenta(self):
        falso = mock.Mock(return_value={"status": "ok"})
        with self._com(nunca=falso), sem_rede():
            st._executar_passo("nunca", {}, tentativas=0)
        falso.assert_not_called()

    def test_resultado_nao_dict_e_sucesso(self):
        casos = [None, [1, 2], "texto", 42, True, 0, ""]
        for valor in casos:
            with self.subTest(valor=repr(valor)):
                with self._com(qualquer=lambda v=valor, **k: v), sem_rede():
                    resultado = st._executar_passo("qualquer", {})
                self.assertEqual(resultado, {"ok": True, "resultado": valor, "erro": None})

    def test_status_em_maiusculas_nao_e_tratado_como_erro(self):
        with self._com(maiusculo=lambda **k: {"status": "OK"}), sem_rede():
            resultado = st._executar_passo("maiusculo", {})
        self.assertTrue(resultado["ok"])

    def test_kwargs_invalidos_nao_propagam(self):
        def estrita(obrigatorio):
            return obrigatorio

        with self._com(estrita=estrita), sem_rede():
            resultado = st._executar_passo("estrita", {"errado": 1})
        self.assertFalse(resultado["ok"])
        self.assertTrue(str(resultado["erro"]).startswith("TypeError"))
        self.assertIsNone(resultado["resultado"])

    def test_ferramenta_nao_chamavel_nao_propaga(self):
        with self._com(nada=None), sem_rede():
            resultado = st._executar_passo("nada", {})
        self.assertFalse(resultado["ok"])
        self.assertIn("TypeError", str(resultado["erro"]))

    def test_args_de_tipo_errado_nao_propagam(self):
        with self._com(eco=lambda **k: k), sem_rede():
            for args in ("texto", 5, ["a"], None):
                with self.subTest(args=repr(args)):
                    try:
                        resultado = st._executar_passo("eco", args)
                    except Exception as exc:  # noqa: BLE001
                        self.fail(f"tipo errado de args propagou {type(exc).__name__}: {exc}")
                    self.assertIn("ok", resultado)

    def test_ferramenta_desconhecida_nao_dorme(self):
        with self._com(), sem_rede():
            st._executar_passo(self.NOME_DESCONHECIDO, {})
        self.assertEqual(st.time.sleep.call_count, 0)


# ============================================================
# 8. simple_task._resposta / _bloquear_acao
# ============================================================

class RespostaTestCase(CasoOffline):

    CHAVES = {"status", "objetivo", "task_id", "plano", "historico",
              "resultado_final", "erro"}

    def test_formato_padrao(self):
        with sem_rede():
            resposta = st._resposta("ok", "objetivo", [])
        self.assertEqual(set(resposta), self.CHAVES)
        self.assertEqual(resposta["status"], "ok")
        self.assertEqual(resposta["objetivo"], "objetivo")
        self.assertIsNone(resposta["task_id"])
        self.assertEqual(resposta["plano"], [])
        self.assertEqual(resposta["historico"], [])
        self.assertIsNone(resposta["resultado_final"])
        self.assertIsNone(resposta["erro"])

    def test_plano_e_derivado_do_historico(self):
        historico = [
            {"passo": 1, "ferramenta": "write_file", "args": {"p": "a"}},
            {"passo": 2, "ferramenta": "code_run", "args": {"codigo": "print(1)"}},
            {"passo": 3},
        ]
        with sem_rede():
            resposta = st._resposta("ok", "obj", historico)
        self.assertEqual(resposta["plano"], [
            {"ferramenta": "write_file", "args": {"p": "a"}},
            {"ferramenta": "code_run", "args": {"codigo": "print(1)"}},
            {"ferramenta": None, "args": None},
        ])

    def test_historico_e_a_mesma_lista(self):
        historico = [{"ferramenta": "f", "args": {}}]
        with sem_rede():
            resposta = st._resposta("ok", "obj", historico)
        self.assertIs(resposta["historico"], historico)

    def test_extra_sobrescreve_e_acrescenta_campos(self):
        with sem_rede():
            resposta = st._resposta(
                "falhou", "obj", [], "task-1",
                resultado_final=None, erro="deu ruim", motivo_encerramento="m",
            )
        self.assertEqual(resposta["task_id"], "task-1")
        self.assertEqual(resposta["erro"], "deu ruim")
        self.assertEqual(resposta["motivo_encerramento"], "m")
        self.assertTrue(self.CHAVES.issubset(set(resposta)))

    def test_objetivo_unicode_emojis_e_muito_longo(self):
        objetivo = "olá \U0001f680 " + "x" * 10000
        with sem_rede():
            resposta = st._resposta("ok", objetivo, [])
        self.assertEqual(resposta["objetivo"], objetivo)

    def test_status_arbitrario_e_preservado(self):
        with sem_rede():
            for status in ("ok", "erro", "cancelado", "pausado", "falhou", "", "\U0001f680"):
                with self.subTest(status=status):
                    self.assertEqual(st._resposta(status, "o", [])["status"], status)

    def test_argumentos_em_falta_levantam_type_error(self):
        with sem_rede():
            with self.assertRaises(TypeError):
                st._resposta("ok", "obj")
            with self.assertRaises(TypeError):
                st._resposta("ok")

    def test_historico_none_ou_nao_iteravel_levanta_type_error(self):
        with sem_rede():
            with self.assertRaises(TypeError):
                st._resposta("ok", "obj", None)
            with self.assertRaises(AttributeError):
                st._resposta("ok", "obj", ["nao_e_dict"])


class BloquearAcaoTestCase(CasoOffline):

    def test_acrescenta_por_ordem_e_sem_duplicados(self):
        bloqueadas = ["f(a=1)"]
        with sem_rede():
            retorno = st._bloquear_acao(bloqueadas, ["f(a=2)", "f(a=1)", "f(a=3)", "f(a=2)"])
        self.assertIsNone(retorno)
        self.assertEqual(bloqueadas, ["f(a=1)", "f(a=2)", "f(a=3)"])

    def test_none_e_lista_vazia_nao_fazem_nada(self):
        bloqueadas = ["x"]
        with sem_rede():
            st._bloquear_acao(bloqueadas, None)
            st._bloquear_acao(bloqueadas, [])
        self.assertEqual(bloqueadas, ["x"])

    def test_aceita_gerador_e_tuplo(self):
        bloqueadas = []
        with sem_rede():
            st._bloquear_acao(bloqueadas, (s for s in ["a", "b"]))
            st._bloquear_acao(bloqueadas, ("c",))
        self.assertEqual(bloqueadas, ["a", "b", "c"])

    def test_unicode_e_emojis_preservados(self):
        bloqueadas = []
        with sem_rede():
            st._bloquear_acao(bloqueadas, ["write_file(caminho='ç', t='\U0001f680')"])
        self.assertEqual(bloqueadas, ["write_file(caminho='ç', t='\U0001f680')"])

    def test_string_solta_e_iterada_caractere_a_caractere(self):
        """Caracterizacao: passar uma string (em vez de lista) adiciona letras."""
        bloqueadas = []
        with sem_rede():
            st._bloquear_acao(bloqueadas, "abc")
        self.assertEqual(bloqueadas, ["a", "b", "c"])

    def test_lista_preexistente_e_mutada_no_sitio(self):
        bloqueadas = []
        with sem_rede():
            st._bloquear_acao(bloqueadas, ["a"])
        self.assertEqual(bloqueadas, ["a"])


# ============================================================
# 9. computer.observer.observar
# ============================================================

class ObserverObservarTestCase(CasoOffline):
    """``observar`` com ``urllib`` substituido: sucesso, lixo e falhas de rede."""

    JSON_OK = ('{"sucesso": true, "objetivo_atingido": true, "motivo": "fez o que pedia", '
               '"proximo_passo_sugerido": ""}')

    def _chamar(self, conteudo=None, corpo=None, erro=None, resposta=None,
                objetivo="objetivo de teste", acao=None):
        if conteudo is not None:
            resposta = resposta_chat(conteudo)
        if resposta is None and corpo is None:
            resposta = resposta_chat("")
        with HTTPFalso(resposta=resposta if resposta is not None else RespostaHTTPFalsa(corpo),
                       erro=erro) as http, sem_rede():
            resultado = observer_mod.observar(objetivo, acao)
        return resultado, http

    def test_json_valido_devolve_os_quatro_campos(self):
        resultado, http = self._chamar(self.JSON_OK)
        self.assertEqual(resultado, {
            "status": "ok", "sucesso": True, "objetivo_atingido": True,
            "motivo": "fez o que pedia", "proximo_passo_sugerido": "",
        })
        self.assertEqual(len(http.pedidos), 1)
        self.assertEqual(http.ultimo["url"], observer_mod.OLLAMA_URL)
        self.assertEqual(http.ultimo["metodo"], "POST")
        payload = http.ultimo["payload"]
        self.assertEqual(payload["model"], observer_mod.OLLAMA_MODEL)
        self.assertIs(payload["stream"], False)
        self.assertEqual(payload["options"], {"temperature": 0.1, "num_predict": 200})
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertIn("objetivo de teste", payload["messages"][0]["content"])

    def test_objetivo_vazio_nao_faz_pedido_nenhum(self):
        for objetivo in ("", None):
            with self.subTest(objetivo=repr(objetivo)):
                with HTTPFalso() as http, sem_rede():
                    resultado = observer_mod.observar(objetivo, {"ferramenta": "f"})
                self.assertEqual(resultado, {"status": "erro", "result": "objetivo vazio"})
                self.assertEqual(http.pedidos, [])

    def test_json_dentro_de_fences_markdown(self):
        for conteudo in (
            f"```json\n{self.JSON_OK}\n```",
            f"```\n{self.JSON_OK}\n```",
            f"Claro!\n```json\n{self.JSON_OK}\n```\nFim.",
        ):
            with self.subTest(conteudo=conteudo[:30]):
                resultado, _ = self._chamar(conteudo)
                self.assertTrue(resultado["sucesso"])
                self.assertTrue(resultado["objetivo_atingido"])

    def test_json_com_texto_extra_a_volta(self):
        for conteudo in (
            f"bla {self.JSON_OK} bla",
            f"Analisei a acao. {self.JSON_OK}",
            f"\ufeff{self.JSON_OK}",
        ):
            with self.subTest(conteudo=conteudo[:30]):
                resultado, _ = self._chamar(conteudo)
                self.assertEqual(resultado["status"], "ok")
                self.assertTrue(resultado["sucesso"])

    def test_prompt_inclui_ferramenta_args_resultado_e_erro(self):
        acao = {
            "ferramenta": "write_file",
            "args": {"caminho": "a.txt", "conteudo": "olá"},
            "resultado": "escrevi 3 linhas",
            "erro": None,
        }
        _, http = self._chamar(self.JSON_OK, acao=acao)
        content = http.ultimo["payload"]["messages"][0]["content"]
        self.assertIn("ACAO EXECUTADA: write_file(", content)
        self.assertIn(json.dumps(acao["args"], ensure_ascii=False), content)
        self.assertIn("escrevi 3 linhas", content)
        self.assertIn("ERRO: (nenhum)", content)

    def test_prompt_sem_acao_anterior_usa_valores_padrao(self):
        _, http = self._chamar(self.JSON_OK, acao=None)
        content = http.ultimo["payload"]["messages"][0]["content"]
        self.assertIn("ACAO EXECUTADA: ?({})", content)
        self.assertIn("RESULTADO: (vazio)", content)
        self.assertIn("ERRO: (nenhum)", content)

    def test_prompt_trunca_resultado_args_e_erro(self):
        args = {"chave": "A" * 900}
        acao = {"ferramenta": "f", "args": args, "resultado": "R" * 5000, "erro": "E" * 900}
        _, http = self._chamar(self.JSON_OK, acao=acao)
        content = http.ultimo["payload"]["messages"][0]["content"]
        self.assertIn("R" * 800, content)
        self.assertNotIn("R" * 801, content)
        self.assertIn("E" * 300, content)
        self.assertNotIn("E" * 301, content)
        self.assertIn(json.dumps(args, ensure_ascii=False)[:200], content)
        self.assertNotIn("A" * 900, content)

    def test_resultado_falsy_e_mostrado_como_vazio(self):
        for valor in ("", 0, {}, [], None):
            with self.subTest(valor=repr(valor)):
                _, http = self._chamar(self.JSON_OK, acao={"resultado": valor})
                self.assertIn("RESULTADO: (vazio)",
                              http.ultimo["payload"]["messages"][0]["content"])

    def test_resultado_nao_string_vira_str_sem_propagar(self):
        for valor in (b"\x00\xff", {"a": 1}, 42, ["x"]):
            with self.subTest(valor=repr(valor)):
                _, http = self._chamar(self.JSON_OK, acao={"resultado": valor})
                self.assertIn("RESULTADO:", http.ultimo["payload"]["messages"][0]["content"])

    def test_chaves_em_falta_usam_valores_padrao(self):
        resultado, _ = self._chamar('{"motivo": "so motivo"}')
        self.assertEqual(resultado, {
            "status": "ok", "sucesso": False, "objetivo_atingido": False,
            "motivo": "so motivo", "proximo_passo_sugerido": "",
        })

    def test_chaves_extra_sao_ignoradas(self):
        resultado, _ = self._chamar(
            '{"sucesso": true, "objetivo_atingido": false, "motivo": "m", '
            '"proximo_passo_sugerido": "p", "confianca": 0.9, "raw": {"x": 1}}'
        )
        self.assertEqual(set(resultado), {"status", "sucesso", "objetivo_atingido",
                                          "motivo", "proximo_passo_sugerido"})
        self.assertEqual(resultado["proximo_passo_sugerido"], "p")

    def test_valores_nao_booleanos_sao_coagidos(self):
        casos = [
            ('"sucesso": "sim"', "sucesso", True),
            ('"sucesso": 1', "sucesso", True),
            ('"sucesso": 0', "sucesso", False),
            ('"sucesso": ""', "sucesso", False),
            ('"sucesso": null', "sucesso", False),
            ('"sucesso": []', "sucesso", False),
            ('"sucesso": {}', "sucesso", False),
            ('"objetivo_atingido": 1', "objetivo_atingido", True),
            ('"objetivo_atingido": 0', "objetivo_atingido", False),
        ]
        for trecho, chave, esperado in casos:
            with self.subTest(trecho=trecho):
                resultado, _ = self._chamar("{%s}" % trecho)
                self.assertEqual(resultado[chave], esperado)

    @unittest.expectedFailure
    def test_string_de_negacao_nao_e_interpretada_como_sucesso(self):
        # BUG: observer.observar faz bool(data.get("sucesso", False)); qualquer
        # string nao vazia vira True. Um LLM que responda {"sucesso": "nao"} e'
        # lido como sucesso -> o ciclo autonomo conclui que a acao funcionou.
        # Evidencia: observar(...) com content '{"sucesso": "nao",
        # "objetivo_atingido": "nao"}' devolve sucesso=True e
        # objetivo_atingido=True (bool("nao") is True).
        resultado, _ = self._chamar('{"sucesso": "nao", "objetivo_atingido": "nao"}')
        self.assertIs(resultado["sucesso"], False)
        self.assertIs(resultado["objetivo_atingido"], False)

    def test_motivo_e_proximo_passo_truncados_em_300(self):
        resultado, _ = self._chamar(
            json.dumps({"sucesso": True, "objetivo_atingido": True,
                        "motivo": "M" * 400, "proximo_passo_sugerido": "P" * 400})
        )
        self.assertEqual(len(resultado["motivo"]), 300)
        self.assertEqual(len(resultado["proximo_passo_sugerido"]), 300)
        self.assertEqual(resultado["motivo"], "M" * 300)

    def test_motivo_nao_string_vira_str(self):
        resultado, _ = self._chamar('{"sucesso": true, "motivo": 123}')
        self.assertEqual(resultado["motivo"], "123")

    def test_texto_sem_json_usa_fallback_com_raw(self):
        texto = "Nao consegui avaliar a acao porque o resultado estava vazio."
        resultado, _ = self._chamar(texto)
        self.assertEqual(resultado["status"], "ok")
        self.assertIsNone(resultado["sucesso"])
        self.assertIsNone(resultado["objetivo_atingido"])
        self.assertEqual(resultado["motivo"], texto)
        self.assertEqual(resultado["raw"], texto)
        self.assertEqual(resultado["proximo_passo_sugerido"], "")

    def test_fallback_trunca_motivo_e_raw(self):
        texto = "sem json " + "Q" * 1000
        resultado, _ = self._chamar(texto)
        self.assertEqual(len(resultado["motivo"]), 300)
        self.assertEqual(len(resultado["raw"]), 500)

    def test_resposta_vazia_ou_objeto_vazio_usa_fallback(self):
        for conteudo, motivo in (("", "(sem resposta)"), ("{}", "{}"), ("[1, 2]", "[1, 2]"),
                                 ("null", "null")):
            with self.subTest(conteudo=conteudo):
                resultado, _ = self._chamar(conteudo)
                self.assertEqual(resultado["status"], "ok")
                self.assertIsNone(resultado["sucesso"])
                self.assertEqual(resultado["motivo"], motivo)

    def test_resposta_do_ollama_sem_message_ou_como_string(self):
        with HTTPFalso(resposta=RespostaHTTPFalsa({"done": True})), sem_rede():
            resultado = observer_mod.observar("obj", None)
        self.assertEqual(resultado["motivo"], "(sem resposta)")

        with HTTPFalso(resposta=RespostaHTTPFalsa({"message": "texto"})), sem_rede():
            resultado = observer_mod.observar("obj", None)
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("erro ao chamar LLM", resultado["result"])

    def test_content_nao_string_devolve_erro_estruturado(self):
        with HTTPFalso(resposta=RespostaHTTPFalsa({"message": {"content": {"a": 1}}})), sem_rede():
            resultado = observer_mod.observar("obj", None)
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("erro ao chamar LLM", resultado["result"])

    def test_corpo_invalido_devolve_erro_estruturado(self):
        corpos = [b"", b"   ", b"<html>502 bad gateway</html>", b"\xff\xfe\x00\x01",
                  b'{"message": ', b"null", b"[1, 2]"]
        for corpo in corpos:
            with self.subTest(corpo=corpo):
                resultado, _ = self._chamar(corpo=corpo)
                self.assertEqual(resultado["status"], "erro")
                self.assertIn("erro ao chamar LLM", resultado["result"])

    def test_http_4xx_5xx_devolvem_erro_estruturado(self):
        # O HTTPError do urllib arrasta um _TemporaryFileWrapper cujo __del__
        # emite ResourceWarning: e' ruido da stdlib, nao do MYRA.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            for codigo in (400, 401, 404, 422, 429, 500, 502, 503):
                with self.subTest(codigo=codigo):
                    resultado, _ = self._chamar(erro=erro_http(codigo))
                    self.assertEqual(resultado["status"], "erro")
                    self.assertIn("erro ao chamar LLM", resultado["result"])
                    self.assertIn(str(codigo), resultado["result"])
            gc.collect()

    def test_timeout_e_falhas_de_rede_devolvem_erro_estruturado(self):
        erros = [
            socket.timeout("timed out"),
            TimeoutError("timeout do urllib"),
            ConnectionRefusedError("recusada"),
            OSError("sem rota"),
            urllib.error.URLError("nome nao resolvido"),
            ValueError("json invalido"),
        ]
        for erro in erros:
            with self.subTest(erro=type(erro).__name__):
                resultado, _ = self._chamar(erro=erro)
                self.assertEqual(resultado["status"], "erro")
                self.assertIn("erro ao chamar LLM", resultado["result"])
                self.assertIn(str(erro), resultado["result"])

    def test_resposta_quebrada_ao_ler_devolve_erro_estruturado(self):
        with HTTPFalso(resposta=RespostaQuebrada()), sem_rede():
            resultado = observer_mod.observar("obj", None)
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("erro ao chamar LLM", resultado["result"])

    def test_resposta_sem_context_manager_devolve_erro_estruturado(self):
        with HTTPFalso(resposta=RespostaSemContexto()), sem_rede():
            resultado = observer_mod.observar("obj", None)
        self.assertEqual(resultado["status"], "erro")

    def test_objetivo_unicode_emojis_e_muito_longo(self):
        objetivo = "objetivo ção \U0001f680 " + "y" * 5000
        resultado, http = self._chamar(self.JSON_OK, objetivo=objetivo)
        self.assertEqual(resultado["status"], "ok")
        self.assertIn(objetivo, http.ultimo["payload"]["messages"][0]["content"])

    def test_sem_rede_a_serio_devolve_erro_estruturado(self):
        """Sem HTTPFalso: a ligacao real e' bloqueada e nada propaga."""
        with sem_rede():
            resultado = observer_mod.observar("objetivo", {"ferramenta": "f"})
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("erro ao chamar LLM", resultado["result"])

    @unittest.expectedFailure
    def test_args_nao_serializaveis_devolvem_erro_estruturado(self):
        # BUG: json.dumps(args) esta FORA do try/except de observar.
        # Evidencia: observar("obj", {"ferramenta": "f", "args": {"x": {1, 2}}})
        # levanta "TypeError: Object of type set is not JSON serializable" em vez
        # de devolver {"status": "erro", ...}. O mesmo acontece com bytes.
        with HTTPFalso(resposta=resposta_chat(self.JSON_OK)), sem_rede():
            resultado = observer_mod.observar(
                "obj", {"ferramenta": "f", "args": {"x": {1, 2}}, "resultado": "r"}
            )
        self.assertEqual(resultado["status"], "erro")


# ============================================================
# 10. tasks.cancel_state (+ integracao minima com executar_task)
# ============================================================

class CancelStateTestCase(CasoCancelamento):

    def test_estado_inicial_limpo(self):
        with sem_rede():
            self.assertFalse(cancel_state.esta_cancelada())
            self.assertFalse(cancel_state.esta_pausada())

    def test_marcar_e_resetar_cancelamento(self):
        with sem_rede():
            self.assertIsNone(cancel_state.marcar_cancelada())
            self.assertTrue(cancel_state.esta_cancelada())
            self.assertIsNone(cancel_state.resetar())
            self.assertFalse(cancel_state.esta_cancelada())

    def test_marcar_e_resetar_pausa(self):
        with sem_rede():
            self.assertIsNone(cancel_state.marcar_pausada())
            self.assertTrue(cancel_state.esta_pausada())
            self.assertIsNone(cancel_state.resetar_pausa())
            self.assertFalse(cancel_state.esta_pausada())

    def test_idempotencia_do_cancelamento_e_da_pausa(self):
        with sem_rede():
            for _ in range(5):
                cancel_state.marcar_cancelada()
                cancel_state.marcar_pausada()
            self.assertTrue(cancel_state.esta_cancelada())
            self.assertTrue(cancel_state.esta_pausada())
            for _ in range(5):
                cancel_state.resetar()
                cancel_state.resetar_pausa()
            self.assertFalse(cancel_state.esta_cancelada())
            self.assertFalse(cancel_state.esta_pausada())

    def test_cancelada_e_pausada_sao_independentes(self):
        with sem_rede():
            cancel_state.marcar_cancelada()
            self.assertTrue(cancel_state.esta_cancelada())
            self.assertFalse(cancel_state.esta_pausada())

            cancel_state.marcar_pausada()
            cancel_state.resetar()
            self.assertFalse(cancel_state.esta_cancelada())
            self.assertTrue(cancel_state.esta_pausada(), "resetar() nao pode limpar a pausa")

            cancel_state.marcar_cancelada()
            cancel_state.resetar_pausa()
            self.assertTrue(cancel_state.esta_cancelada(), "resetar_pausa() nao limpa o cancelamento")
            self.assertFalse(cancel_state.esta_pausada())

    def test_valores_de_retorno_sao_bool(self):
        with sem_rede():
            self.assertIs(cancel_state.esta_cancelada(), False)
            self.assertIs(cancel_state.esta_pausada(), False)
            cancel_state.marcar_cancelada()
            self.assertIs(cancel_state.esta_cancelada(), True)

    def test_estado_e_partilhado_com_simple_task(self):
        """``simple_task`` importou as funcoes: tem de ver o mesmo estado global."""
        with sem_rede():
            cancel_state.marcar_cancelada()
            self.assertTrue(st.esta_cancelada())
            cancel_state.resetar()
            self.assertFalse(st.esta_cancelada())

            cancel_state.marcar_pausada()
            self.assertTrue(st.esta_pausada())
            cancel_state.resetar_pausa()
            self.assertFalse(st.esta_pausada())

    def test_simple_task_le_os_globais_do_modulo_de_estado(self):
        """Mexer diretamente nos globais de ``cancel_state`` muda a resposta."""
        with sem_rede():
            with mock.patch.object(cancel_state, "_cancelada", True):
                self.assertTrue(st.esta_cancelada())
            with mock.patch.object(cancel_state, "_pausada", True):
                self.assertTrue(st.esta_pausada())
            self.assertFalse(st.esta_cancelada())
            self.assertFalse(st.esta_pausada())

    def test_importar_de_novo_devolve_o_mesmo_modulo(self):
        with sem_rede():
            self.assertIs(importlib.import_module("tasks.cancel_state"), cancel_state)

    def test_reload_do_modulo_limpa_o_estado(self):
        """Caracterizacao: o estado vive em memoria (reload -> limpo)."""
        with sem_rede():
            cancel_state.marcar_cancelada()
            cancel_state.marcar_pausada()
            importlib.reload(cancel_state)
            self.addCleanup(cancel_state.resetar)
            self.addCleanup(cancel_state.resetar_pausa)
            self.assertFalse(cancel_state.esta_cancelada())
            self.assertFalse(cancel_state.esta_pausada())


class CancelamentoNaTaskTestCase(CasoCancelamento):
    """Integracao minima: o loop da task respeita cancelamento e pausa."""

    def _rodar(self):
        with mock.patch.dict(st.FERRAMENTAS_DISPONIVEIS,
                             {"ferramenta_falsa": lambda **k: {"status": "ok"}}, clear=True), \
             mock.patch.object(st, "_widget_notify"), sem_rede():
            return st.executar_task("objetivo de teste", max_passos=3, persistir=False)

    def test_task_cancelada_aborta_sem_executar_nada(self):
        with sem_rede():
            cancel_state.marcar_cancelada()
            resultado = self._rodar()
        self.assertEqual(resultado["status"], "cancelado")
        self.assertEqual(resultado["historico"], [])
        self.assertEqual(resultado["plano"], [])
        self.assertIsNone(resultado["task_id"])

    def test_task_pausada_para_sem_perder_historico(self):
        with sem_rede():
            cancel_state.marcar_pausada()
            resultado = self._rodar()
        self.assertEqual(resultado["status"], "pausado")
        self.assertEqual(resultado["historico"], [])
        self.assertEqual(resultado["passo_atual"], 0)
        self.assertIsNone(resultado["erro"])

    def test_cancelamento_tem_prioridade_sobre_a_pausa(self):
        with sem_rede():
            cancel_state.marcar_cancelada()
            cancel_state.marcar_pausada()
            resultado = self._rodar()
        self.assertEqual(resultado["status"], "cancelado")

    def test_sem_cancelamento_nem_pausa_o_estado_nao_interfere(self):
        """Sem cancelamento, o loop chega ao planner - que aqui nao e' chamado
        porque a ferramenta registada nao faz nada de rede: apenas confirmamos
        que o estado limpo nao devolve "cancelado"/"pausado" antes do tempo."""
        with sem_rede():
            cancel_state.resetar()
            cancel_state.resetar_pausa()
            self.assertFalse(st.esta_cancelada())
            self.assertFalse(st.esta_pausada())


if __name__ == "__main__":
    unittest.main(verbosity=2)
