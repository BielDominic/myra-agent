# -*- coding: utf-8 -*-
"""Testes severos de ``tools/visuals_core.py`` (tabelas, graficos, timelines, arvores).

O modulo e **puro**: nao abre sockets, nao escreve ficheiros e nao toca no PC.
Ainda assim os testes correm com ``AmbienteIsolado`` (via ``CasoBase``) e existe
um teste dedicado que executa todas as ferramentas dentro de ``sem_rede()`` para
provar que nada tenta falar com o Ollama (:11434), com o backend (:8000), com o
servico de visao (:8081), com o Gmail ou com a Internet.

Convencoes verificadas (contrato real das ferramentas OpenWebUI):

* Sucesso em ``mode="text"`` devolve ``str`` (Markdown + bloco ASCII).
* Sucesso em ``mode="embed"`` devolve ``HTMLResponse`` (200, ``text/html``,
  ``Content-Disposition: inline``).
* **Erro nunca levanta excepcao**: devolve sempre uma mensagem ``str``
  (ex.: ``"Invalid 'rows': expected a list of objects."``). Os testes abaixo
  verificam esse contrato com listas de valores degenerados.

Bugs de producao encontrados estao nos testes ``test_bug_*`` marcados com
``@unittest.expectedFailure`` e comentario ``BUG:`` (nenhum ficheiro de producao
foi alterado).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import unittest

from tests.helpers import CasoBase, sem_rede
from tools.visuals_core import HTMLResponse, Tools

# ============================================================
# Utilitarios
# ============================================================


def _executar(resultado):
    """Resolve o retorno de uma ferramenta (coroutine) num valor concreto."""
    if inspect.iscoroutine(resultado):
        return asyncio.run(resultado)
    return resultado


def _texto(resultado) -> str:
    """Corpo textual de um ``str`` ou de um ``HTMLResponse``."""
    corpo = getattr(resultado, "body", resultado)
    if isinstance(corpo, bytes):
        return corpo.decode("utf-8", "replace")
    return str(corpo)


def _payload(pagina: str, nome: str):
    """Extrai e desserializa ``const <nome> = {...};`` do bloco <script> do Plotly."""
    encontrado = re.search(r"const %s = (.*?);\n" % re.escape(nome), pagina, re.S)
    if encontrado is None:  # pragma: no cover - diagnostico de falha
        raise AssertionError("payload %r nao encontrado no HTML gerado" % nome)
    return json.loads(encontrado.group(1))


def _linhas_eixo(texto: str) -> int:
    """Numero de linhas de eixo (``  12.0 │...``) de um grafico ASCII."""
    return sum(1 for linha in texto.split("\n") if re.match(r"^\s*-?\d+\.\d+ │", linha))


class CasoVisual(CasoBase):
    """Base: isolamento de ambiente por teste (``CasoBase``) + instancia limpa."""

    def setUp(self) -> None:
        super().setUp()
        self.t = Tools()

    def render(self, resultado):
        return _executar(resultado)

    def texto(self, resultado) -> str:
        return _texto(self.render(resultado))

    def _excecoes(self, casos) -> list:
        """Executa callables e devolve as excepcoes que escaparam (nao levanta)."""
        falhas = []
        for nome, chamada in casos:
            try:
                _texto(self.render(chamada()))
            except Exception as exc:  # noqa: BLE001 - queremos ver o que escapa
                falhas.append(f"{nome}: {type(exc).__name__}: {exc}")
        return falhas


# ============================================================
# render_table
# ============================================================


class CasoRenderTable(CasoVisual):
    def test_texto_estrutura_markdown_exata(self):
        saida = self.texto(self.t.render_table([{"a": 1, "b": "x"}], mode="text"))
        self.assertEqual("### Table\n\n| a | b |\n| --- | --- |\n| 1 | x |", saida)

    def test_titulo_personalizado_unicode_e_titulo_vazio(self):
        com_titulo = self.texto(self.t.render_table([{"a": 1}], title="Relatório 🚀", mode="text"))
        self.assertTrue(com_titulo.startswith("### Relatório 🚀\n\n"))
        self.assertEqual("| a |\n| --- |\n| 1 |", self.texto(self.t.render_table([{"a": 1}], title="", mode="text")))

    def test_uniao_de_colunas_ordem_primeira_vista_e_celulas_em_falta(self):
        saida = self.texto(self.t.render_table([{"a": 1, "b": 2}, {"c": 3, "a": 4}], mode="text"))
        linhas = saida.split("\n")
        self.assertEqual("| a | b | c |", linhas[2])
        self.assertEqual("| 1 | 2 |  |", linhas[4])
        self.assertEqual("| 4 |  | 3 |", linhas[5])

    def test_none_zero_vazio_newline_e_unicode(self):
        saida = self.texto(
            self.t.render_table(
                [{"n": None, "z": 0, "e": "", "u": "🚀 ção", "m": "a\nb"}], mode="text"
            )
        )
        self.assertEqual("|  | 0 |  | 🚀 ção | a b |", saida.split("\n")[4])
        self.assertNotIn("a\nb", saida)

    def test_entradas_invalidas_devolvem_erro_textual(self):
        self.assertEqual("No valid rows provided.", self.texto(self.t.render_table([], mode="text")))
        self.assertEqual("No valid rows provided.", self.texto(self.t.render_table("[]", mode="text")))
        for entrada in (None, {"a": 1}, "texto", 3.14, True):
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    "Invalid 'rows': expected a list of objects.",
                    self.texto(self.t.render_table(entrada, mode="text")),
                )
        self.assertEqual(
            "Invalid row at index 1: expected dict, got int.",
            self.texto(self.t.render_table([{"a": 1}, 5], mode="text")),
        )

    def test_json_string_escapado_duplicado_e_aspas(self):
        self.assertIn("| 2 |", self.texto(self.t.render_table('[{"a": 1, "a": 2}]', mode="text")))
        self.assertIn("| 1 |", self.texto(self.t.render_table("[{&quot;a&quot;: 1}]", mode="text")))
        envolvido = '"' + json.dumps([{"a": 1}]) + '"'
        self.assertIn("| 1 |", self.texto(self.t.render_table(envolvido, mode="text")))
        self.assertEqual(
            "Invalid 'rows': expected a list of objects.",
            self.texto(self.t.render_table("[{a: 1}]", mode="text")),
        )

    def test_1000_linhas_respeita_limite_e_tempo(self):
        linhas = [{"i": i, "v": i * 2} for i in range(1000)]
        inicio = time.perf_counter()
        saida = self.texto(self.t.render_table(linhas, mode="text"))
        decorrido = time.perf_counter() - inicio
        linhas_md = [linha for linha in saida.split("\n") if linha.startswith("| ")]
        self.assertEqual(self.t.valves.max_rows + 2, len(linhas_md))  # cabecalho + separador
        self.assertLess(decorrido, 5.0)
        pagina = self.texto(self.t.render_table(linhas, mode="embed"))
        self.assertEqual(self.t.valves.max_rows + 1, pagina.count("<tr>"))  # thead + corpo

    def test_limites_configuraveis_max_rows_e_max_cols(self):
        self.t.valves.max_rows = 3
        self.t.valves.max_cols = 2
        linhas = [{"a": i, "b": i, "c": i} for i in range(6)]
        saida = self.texto(self.t.render_table(linhas, mode="text"))
        self.assertEqual("| a | b |", saida.split("\n")[2])
        self.assertEqual(5, len([linha for linha in saida.split("\n") if linha.startswith("| ")]))
        self.assertNotIn("| c |", saida)

    def test_html_estrutura_e_escaping_de_injecao(self):
        titulo = "</title><script>alert('t')</script>"
        chave = "<script>alert(1)</script>"
        valor = "<img src=x onerror=alert(2)>"
        resposta = self.render(self.t.render_table([{chave: valor}], title=titulo, mode="embed"))
        self.assertIsInstance(resposta, HTMLResponse)
        self.assertEqual(200, resposta.status_code)
        self.assertEqual("text/html", resposta.media_type)
        self.assertEqual("utf-8", resposta.charset)
        self.assertEqual("inline", resposta.headers["content-disposition"])
        pagina = _texto(resposta)
        self.assertIn("<!doctype html>", pagina)
        self.assertTrue(pagina.rstrip().endswith("</html>"))
        self.assertIn("<table>", pagina)
        self.assertIn("<th", pagina)
        self.assertIn("<td", pagina)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", pagina)
        self.assertNotIn("<script>alert", pagina)
        self.assertNotIn("<img src=x", pagina)
        self.assertEqual(1, pagina.count("<title>"))
        self.assertIn("&lt;/title&gt;", pagina)

    def test_html_alinhamento_numerico_e_coluna_booleana(self):
        pagina = self.texto(self.t.render_table([{"nome": "a", "valor": 10}], mode="embed"))
        self.assertIn("text-align:right", pagina)
        self.assertIn("text-align:left", pagina)
        booleana = self.texto(self.t.render_table([{"flag": True}], mode="embed"))
        self.assertNotIn("text-align:right", booleana)
        com_none = self.texto(self.t.render_table([{"v": None}, {"v": 2}], mode="embed"))
        self.assertIn("text-align:right", com_none)

    def test_modo_desconhecido_nao_levanta(self):
        self.assertIsInstance(self.render(self.t.render_table([{"a": 1}], mode="banana")), HTMLResponse)

    def test_caracteres_perigosos_e_string_muito_longa(self):
        rotulo = "<img src=x onerror=alert(1)>" + "ç" * 5000 + "\x00" + '"\'&<>'
        saida = self.texto(self.t.render_table([{"c": rotulo}], mode="text"))
        self.assertIn("ç" * 5000, saida)
        self.assertGreater(len(saida), 5000)
        pagina = self.texto(self.t.render_table([{"c": rotulo}], mode="embed"))
        self.assertNotIn("<img src=x", pagina)
        self.assertIn("&lt;img src=x", pagina)
        self.assertIn("&amp;", pagina)


# ============================================================
# render_comparison_table
# ============================================================


class CasoRenderComparisonTable(CasoVisual):
    def test_texto_marca_melhores_valores(self):
        saida = self.texto(
            self.t.render_comparison_table(
                ["A", "B"],
                ["preco", "qualidade"],
                {"A": {"preco": 10, "qualidade": 9}, "B": {"preco": 5, "qualidade": 8}},
                mode="text",
            )
        )
        self.assertEqual(
            "### Comparison\n\n| Item | preco | qualidade |\n| --- | --- | --- |\n"
            "| A | 10 ★ | 9 ★ |\n| B | 5 | 8 |",
            saida,
        )

    def test_melhores_valores_com_strings_numericas_e_negativos(self):
        saida = self.texto(
            self.t.render_comparison_table(
                ["A", "B"], ["p"], {"A": {"p": "-5"}, "B": {"p": "-10"}}, mode="text"
            )
        )
        self.assertIn("| A | -5 ★ |", saida)
        self.assertIn("| B | -10 |", saida)

    def test_item_sem_score_usa_travessao(self):
        saida = self.texto(self.t.render_comparison_table(["A"], ["c"], {"A": {}}, mode="text"))
        self.assertIn("| A | — |", saida)

    def test_highlight_desligado_nao_marca(self):
        saida = self.texto(
            self.t.render_comparison_table(
                ["A", "B"], ["p"], {"A": {"p": 1}, "B": {"p": 2}}, highlight_best=False, mode="text"
            )
        )
        self.assertNotIn("★", saida)

    def test_scores_invalidos_nao_levantam(self):
        for scores in ("nao json", [1, 2], None, {"A": "texto"}, {"A": None}, 7, "{}"):
            with self.subTest(scores=scores):
                saida = self.texto(self.t.render_comparison_table(["A", "B"], ["c"], scores, mode="text"))
                self.assertIn("—", saida)
                self.assertNotIn("★", saida)

    def test_items_e_criteria_em_json_string_ou_escalar(self):
        saida = self.texto(self.t.render_comparison_table('["A","B"]', 7, {}, mode="text"))
        self.assertEqual("### Comparison\n\n| Item |\n| --- |\n| A |\n| B |", saida)
        escalar = self.texto(self.t.render_comparison_table("A", "c", {"A": {"c": 1}}, mode="text"))
        self.assertIn("| A | 1 ★ |", escalar)

    def test_listas_vazias_devolvem_apenas_cabecalho(self):
        self.assertEqual(
            "### Comparison\n\n| Item |\n| --- |\n",
            self.texto(self.t.render_comparison_table([], [], {}, mode="text")),
        )

    def test_html_escapa_injecao_e_destaca_melhor_valor(self):
        item = "<script>alert(1)</script>"
        criterio = "<b>&"
        resposta = self.render(
            self.t.render_comparison_table(
                [item],
                [criterio],
                {item: {criterio: 5}},
                title="</title><script>alert(9)</script>",
                mode="embed",
            )
        )
        self.assertIsInstance(resposta, HTMLResponse)
        pagina = _texto(resposta)
        self.assertNotIn("<script>alert", pagina)
        self.assertNotIn("<b>&", pagina)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)
        self.assertIn("background:#14532d", pagina)
        self.assertNotIn("★", pagina)
        self.assertEqual(1, pagina.count("<title>"))
        self.assertIn("&lt;/title&gt;", pagina)

    def test_html_sem_highlight_nao_pinta_fundo_verde(self):
        resposta = self.render(
            self.t.render_comparison_table(
                ["A", "B"], ["p"], {"A": {"p": 1}, "B": {"p": 2}}, highlight_best=False, mode="embed"
            )
        )
        self.assertNotIn("#14532d", _texto(resposta))


# ============================================================
# render_chart / render_multi_chart
# ============================================================


class CasoRenderChart(CasoVisual):
    def test_texto_estrutura_ascii_e_altura_padrao(self):
        saida = self.texto(
            self.t.render_chart(["Mon", "Tue", "Wed"], [120, 180, 160], title="Sessões", mode="text")
        )
        self.assertTrue(saida.startswith("### Sessões\n\n```text\n"))
        self.assertTrue(saida.endswith("```"))
        self.assertIn("●", saida)
        self.assertIn("┴", saida)
        self.assertIn("Mon Tue Wed", saida)
        self.assertEqual(self.t.valves.ascii_chart_height, _linhas_eixo(saida))

    def test_comprimentos_diferentes_devolvem_erro_com_contagens(self):
        self.assertEqual(
            "x and y must have the same length (got 3 and 2).",
            self.texto(self.t.render_chart(["a", "b", "c"], [1, 2], mode="text")),
        )
        self.assertEqual(
            "x and y must have the same length (got 2 and 0).",
            self.texto(self.t.render_chart(["a", "b"], ["x", "y"], mode="text")),
        )

    def test_entradas_invalidas_de_x_e_y(self):
        self.assertEqual(
            "Invalid 'x': expected a list.",
            self.texto(self.t.render_chart({"a": 1}, [1], mode="text")),
        )
        self.assertEqual(
            "Invalid 'x': expected a list.", self.texto(self.t.render_chart(None, [1], mode="text"))
        )
        self.assertEqual(
            "No data provided (x and y are empty).",
            self.texto(self.t.render_chart([], [], mode="text")),
        )

    def test_coage_strings_numericas_e_json_string(self):
        saida = self.texto(self.t.render_chart('["a", "b"]', '["1.5", "2"]', mode="text"))
        self.assertIn("●", saida)
        self.assertIn("2.0 │", saida)
        self.assertEqual(self.t.valves.ascii_chart_height, _linhas_eixo(saida))

    def test_negativos_zero_iguais_e_um_item(self):
        negativos = self.texto(self.t.render_chart(["a", "b", "c"], [-5, 0, 5], mode="text"))
        self.assertIn("-5.0 │", negativos)
        self.assertIn(" 5.0 │", negativos)
        for y in ([3, 3], [0, 0], [1], [0.0], [-1.5], [1, 2, 3, 4, 5]):
            with self.subTest(y=y):
                saida = self.texto(
                    self.t.render_chart([str(i) for i in range(len(y))], y, mode="text")
                )
                self.assertIn("```text", saida)
                self.assertIn("●", saida)

    def test_tipos_de_grafico_validos_e_desconhecidos(self):
        for tipo in ("line", "bar", "scatter", "pie", "BAR", " bar "):
            with self.subTest(chart_type=tipo):
                saida = self.texto(self.t.render_chart(["a", "b"], [1, 2], chart_type=tipo, mode="text"))
                self.assertTrue(saida.startswith("### Chart"))
                self.assertIn("```text", saida)
        barra = self.texto(self.t.render_chart(["a", "b"], [1, 2], chart_type="bar", mode="text"))
        self.assertIn("█", barra)
        dispersao = self.texto(self.t.render_chart(["a", "b"], [1, 2], chart_type="scatter", mode="text"))
        self.assertNotIn("─", dispersao)
        linha = self.texto(self.t.render_chart(["a", "b"], [1, 2], chart_type="line", mode="text"))
        self.assertGreater(linha.count("│"), dispersao.count("│"))

    def test_embed_gera_plotly_com_payload_json(self):
        resposta = self.render(
            self.t.render_chart(
                ["a", "b"], [1, 2], title="T", x_label="Eixo X", y_label="Eixo Y", mode="embed"
            )
        )
        self.assertIsInstance(resposta, HTMLResponse)
        pagina = _texto(resposta)
        self.assertIn("cdn.plot.ly/plotly-2.27.0.min.js", pagina)
        self.assertIn("Plotly.newPlot(", pagina)
        self.assertIn('id="chart_', pagina)
        trace = _payload(pagina, "trace")
        self.assertEqual(
            {"x": ["a", "b"], "y": [1.0, 2.0], "type": "scatter", "mode": "lines+markers"}, trace
        )
        layout = _payload(pagina, "layout")
        self.assertEqual("T", layout["title"]["text"])
        self.assertEqual("Eixo X", layout["xaxis"]["title"]["text"])
        self.assertEqual("Eixo Y", layout["yaxis"]["title"]["text"])
        self.assertEqual("#0b0f14", layout["paper_bgcolor"])

    def test_embed_tipo_barra_nao_usa_mode_e_e_deterministico(self):
        primeira = self.texto(self.render(self.t.render_chart(["a"], [1], chart_type="bar", mode="embed")))
        trace = _payload(primeira, "trace")
        self.assertEqual("bar", trace["type"])
        self.assertNotIn("mode", trace)
        segunda = self.texto(self.render(self.t.render_chart(["a"], [1], chart_type="bar", mode="embed")))
        self.assertEqual(primeira, segunda)


class CasoRenderMultiChart(CasoVisual):
    def test_texto_com_varias_series(self):
        saida = self.texto(
            self.t.render_multi_chart(
                [{"name": "A", "x": ["p"], "y": [1]}, {"name": "B", "x": ["q"], "y": [2]}], mode="text"
            )
        )
        self.assertTrue(saida.startswith("### Chart\n\n### A\n\n```text"))
        self.assertIn("### B", saida)
        self.assertEqual(2, saida.count("```text"))

    def test_serie_sem_dados_e_sem_nome(self):
        saida = self.texto(self.t.render_multi_chart([{"name": "s"}], mode="text"))
        self.assertIn("### s", saida)
        self.assertIn("No data to display.", saida)
        sem_nome = self.texto(self.t.render_multi_chart([{"x": ["a"], "y": [1]}], mode="text"))
        self.assertIn("### Series", sem_nome)

    def test_entradas_invalidas(self):
        self.assertEqual("No valid series items found.", self.texto(self.t.render_multi_chart([], mode="text")))
        for entrada in ({}, None, "texto", 3):
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    "Invalid 'series': expected a list of objects.",
                    self.texto(self.t.render_multi_chart(entrada, mode="text")),
                )
        self.assertEqual(
            "Invalid series item at index 1: expected dict, got str.",
            self.texto(self.t.render_multi_chart([{"x": [], "y": []}, "x"], mode="text")),
        )

    def test_embed_traces_json_com_nomes_e_tipos(self):
        resposta = self.render(
            self.t.render_multi_chart(
                [{"name": "A", "x": ["p"], "y": [1]}, {"name": "B", "x": ["q"], "y": [2]}],
                chart_type="bar",
                mode="embed",
            )
        )
        pagina = _texto(resposta)
        self.assertIn('id="multichart_', pagina)
        traces = _payload(pagina, "traces")
        self.assertEqual(2, len(traces))
        self.assertEqual(["A", "B"], [t["name"] for t in traces])
        self.assertEqual(["bar", "bar"], [t["type"] for t in traces])
        self.assertEqual([[1.0], [2.0]], [t["y"] for t in traces])


# ============================================================
# render_line_chart / render_bar_chart
# ============================================================


class CasoRenderLineChart(CasoVisual):
    def test_altura_limites_e_restauro_dos_valves(self):
        for altura, esperado in ((0, 5), (1, 5), (12.9, 12), (40, 40), (999, 40)):
            with self.subTest(height=altura):
                saida = self.texto(self.t.render_line_chart(["a", "b"], [1, 2], height=altura))
                self.assertEqual(esperado, _linhas_eixo(saida))
                self.assertEqual(12, self.t.valves.ascii_chart_height)
        como_string = self.texto(self.t.render_line_chart(["a", "b"], [1, 2], height="7"))
        self.assertEqual(7, _linhas_eixo(como_string))

    def test_dados_vazios_e_tipos_invalidos(self):
        self.assertEqual(
            "No data provided (y values are empty).",
            self.texto(self.t.render_line_chart(["a"], [], height=5)),
        )
        self.assertEqual(
            "No data provided (y values are empty).",
            self.texto(self.t.render_line_chart(["a"], ["nao-numero"], height=5)),
        )
        for x in ("texto", None, {"a": 1}, 7):
            with self.subTest(x=x):
                self.assertEqual(
                    "Invalid 'x': expected a list.",
                    self.texto(self.t.render_line_chart(x, [1], height=5)),
                )

    def test_json_string_unicode_e_titulo(self):
        saida = self.texto(self.t.render_line_chart('["🚀", "ç"]', "[1, 2]", title="Ünïcødé", height=6))
        self.assertTrue(saida.startswith("### Ünïcødé"))
        self.assertIn("🚀", saida)
        self.assertIn("●", saida)
        self.assertEqual(6, _linhas_eixo(saida))

    def test_x_mais_curto_que_y_nao_levanta(self):
        saida = self.texto(self.t.render_line_chart(["a"], [1, 2, 3], height=6))
        self.assertIn("```text", saida)
        self.assertIn("●", saida)


class CasoRenderBarChart(CasoVisual):
    def test_estrutura_altura_e_rotulos(self):
        saida = self.texto(self.t.render_bar_chart(["A", "B"], [1, 4], height=6))
        self.assertTrue(saida.startswith("### Bar Chart\n\n```text\n"))
        self.assertIn("█", saida)
        self.assertIn("┴┴┴┴", saida)
        self.assertIn("A", saida)
        self.assertIn("B", saida)
        self.assertEqual(6, _linhas_eixo(saida))
        self.assertEqual(12, self.t.valves.ascii_chart_height)

    def test_altura_limites(self):
        self.assertEqual(5, _linhas_eixo(self.texto(self.t.render_bar_chart(["a", "b"], [1, 2], height=0))))
        self.assertEqual(
            40, _linhas_eixo(self.texto(self.t.render_bar_chart(["a", "b"], [1, 2], height=10 ** 9)))
        )

    def test_valores_iguais_zero_e_negativos_nao_dividem_por_zero(self):
        for y in ([3, 3], [0, 0], [-1, -2], [-5, 0, 5], [0.5]):
            with self.subTest(y=y):
                saida = self.texto(
                    self.t.render_bar_chart([str(i) for i in range(len(y))], y, height=6)
                )
                self.assertEqual(6, _linhas_eixo(saida))
                self.assertIn("```text", saida)

    def test_dados_vazios_e_x_invalido(self):
        self.assertEqual(
            "No data provided (y values are empty).",
            self.texto(self.t.render_bar_chart(["a"], [], height=5)),
        )
        self.assertEqual(
            "Invalid 'x': expected a list.",
            self.texto(self.t.render_bar_chart({"a": 1}, [1], height=5)),
        )


# ============================================================
# render_heatmap
# ============================================================


class CasoRenderHeatmap(CasoVisual):
    def test_texto_labels_automaticas_e_intervalo(self):
        saida = self.texto(self.t.render_heatmap([[1, 2], [3, 4]], [], [], mode="text"))
        for esperado in ("### Heatmap", "```text", "Row 1", "Row 2", "Col 1", "Col 2", "Range: 1.00 to 4.00"):
            self.assertIn(esperado, saida)

    def test_labels_fornecidas_e_menos_labels_que_linhas(self):
        saida = self.texto(
            self.t.render_heatmap([[1, 2], [3, 4], [5, 6]], ["r1"], ["c1", "c2"], mode="text")
        )
        self.assertIn("r1", saida)
        self.assertIn("c1", saida)
        self.assertNotIn("Row 2", saida)
        self.assertIn("Range: 1.00 to 6.00", saida)

    def test_linhas_irregulares_no_texto_e_rectangular_no_embed(self):
        texto = self.texto(self.t.render_heatmap([[1, 2, 3], [4]], [], [], mode="text"))
        self.assertIn("Col 3", texto)
        pagina = _texto(self.render(self.t.render_heatmap([[1], [2, 3]], [], [], mode="embed")))
        trace = _payload(pagina, "trace")
        self.assertEqual("heatmap", trace["type"])
        self.assertEqual([[1.0, 0.0], [2.0, 3.0]], trace["z"])
        self.assertEqual(["Col 1", "Col 2"], trace["x"])
        self.assertEqual(["Row 1", "Row 2"], trace["y"])
        self.assertIs(False, trace["hoverongaps"])

    def test_limite_max_rows(self):
        self.assertEqual(
            "Data too large: 251 rows exceeds max_rows=250.",
            self.texto(self.t.render_heatmap([[1]] * 251, [], [], mode="text")),
        )
        self.assertTrue(
            self.texto(self.t.render_heatmap([[1]] * 250, [], [], mode="text")).startswith("### Heatmap")
        )

    def test_entradas_invalidas_e_valores_coagidos(self):
        for entrada in ("nao json", {"a": 1}, [], None, 7, True):
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    "No valid heatmap data provided.",
                    self.texto(self.t.render_heatmap(entrada, [], [], mode="text")),
                )
        saida = self.texto(self.t.render_heatmap([["a", None, "3"]], [], [], mode="text"))
        self.assertIn("Range: 0.00 to 3.00", saida)

    def test_cap_de_colunas(self):
        self.t.valves.max_cols = 2
        saida = self.texto(self.t.render_heatmap([[1, 2, 3]], ["r"], ["A1", "B1", "C1"], mode="text"))
        self.assertIn("A1", saida)
        self.assertIn("B1", saida)
        self.assertNotIn("C1", saida)

    def test_embed_estrutura_plotly(self):
        resposta = self.render(self.t.render_heatmap([[1, 2]], ["r1"], ["c1", "c2"], mode="embed"))
        self.assertIsInstance(resposta, HTMLResponse)
        pagina = _texto(resposta)
        self.assertIn("cdn.plot.ly/plotly-2.27.0.min.js", pagina)
        self.assertIn('id="heat_', pagina)
        trace = _payload(pagina, "trace")
        self.assertEqual(["c1", "c2"], trace["x"])
        self.assertEqual(["r1"], trace["y"])
        self.assertEqual([[1.0, 2.0]], trace["z"])

    def test_labels_escalares_usam_automaticas_e_string_json(self):
        saida = self.texto(self.t.render_heatmap([[1, 2]], 5, '["x","y"]', mode="text"))
        self.assertIn("Row 1", saida)
        self.assertIn("x", saida)
        self.assertIn("y", saida)


# ============================================================
# render_timeline
# ============================================================


class CasoRenderTimeline(CasoVisual):
    def test_texto_com_datas_detalhes_e_valores_em_falta(self):
        saida = self.texto(
            self.t.render_timeline(
                [{"date": "2026-01-01", "label": "Kickoff", "detail": "d"}, {"date": "2026-02-01", "label": ""}, {}],
                mode="text",
            )
        )
        self.assertEqual(
            "### Timeline\n\n```text\n2026-01-01 — Kickoff :: d\n2026-02-01 — Event\nEvent\n```", saida
        )

    def test_show_dates_false_e_unicode(self):
        sem_datas = self.texto(
            self.t.render_timeline([{"date": "2026-01-01", "label": "🚀 início"}], show_dates=False, mode="text")
        )
        self.assertEqual("### Timeline\n\n```text\n🚀 início\n```", sem_datas)
        com_data = self.texto(self.t.render_timeline([{"date": "2026-01-01", "label": "🚀"}], mode="text"))
        self.assertIn("2026-01-01 — 🚀", com_data)

    def test_entradas_invalidas(self):
        self.assertEqual("No events provided.", self.texto(self.t.render_timeline([], mode="text")))
        for entrada in ({"date": "x"}, None, "texto", 5, True):
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    "Invalid 'events': expected a list of objects.",
                    self.texto(self.t.render_timeline(entrada, mode="text")),
                )
        self.assertEqual(
            "Invalid event at index 0: expected dict, got str.",
            self.texto(self.t.render_timeline(["a"], mode="text")),
        )
        self.assertEqual(
            "Invalid event at index 1: expected dict, got int.",
            self.texto(self.t.render_timeline([{"label": "a"}, 3], mode="text")),
        )

    def test_html_escapa_injecao_no_pre(self):
        resposta = self.render(
            self.t.render_timeline(
                [{"date": "2026", "label": "</pre></div><script>alert(1)</script>", "detail": "<b>&"}],
                title="</title><script>alert(2)</script>",
                mode="embed",
            )
        )
        self.assertIsInstance(resposta, HTMLResponse)
        pagina = _texto(resposta)
        self.assertNotIn("<script>alert", pagina)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)
        self.assertIn("&lt;b&gt;&amp;", pagina)
        self.assertNotIn("<b>", pagina)
        self.assertEqual(1, pagina.count("</pre>"))
        self.assertEqual(1, pagina.count("<title>"))
        self.assertIn("&lt;/title&gt;", pagina)

    def test_titulo_vazio(self):
        self.assertEqual(
            "```text\na\n```", self.texto(self.t.render_timeline([{"label": "a"}], title="", mode="text"))
        )
        pagina = _texto(self.render(self.t.render_timeline([{"label": "a"}], title="", mode="embed")))
        self.assertIn("<title>Visual</title>", pagina)


# ============================================================
# render_flowchart
# ============================================================


class CasoRenderFlowchart(CasoVisual):
    def test_top_bottom_e_left_right(self):
        tb = self.texto(
            self.t.render_flowchart(
                [{"from": "A", "to": "B"}, {"from": "A", "to": "C", "label": "z"}], mode="text"
            )
        )
        self.assertEqual("### Flowchart\n\n```text\n[A] --> [B]\n[A] --z--> [C]\n```", tb)
        lr = self.texto(
            self.t.render_flowchart(
                [{"from": "A", "to": "B", "label": "ok"}, {"from": "B", "to": "C"}],
                direction="lr",
                mode="text",
            )
        )
        self.assertIn("[A] --ok--> [B] ----> [C]", lr)

    def test_ciclos_duplicados_e_auto_lacos(self):
        ciclo = self.texto(
            self.t.render_flowchart(
                [{"from": "A", "to": "B"}, {"from": "B", "to": "A"}, {"from": "A", "to": "B"}], mode="text"
            )
        )
        self.assertEqual(3, len([linha for linha in ciclo.split("\n") if linha.startswith("[")]))
        self.assertEqual(
            "### Flowchart\n\n```text\n[A] --> [A]\n```",
            self.texto(self.t.render_flowchart([{"from": "A", "to": "A"}], mode="text")),
        )
        lr = self.texto(self.t.render_flowchart([{"from": "A", "to": "A"}], direction="lr", mode="text"))
        self.assertIn("[A]", lr)

    def test_entradas_invalidas(self):
        sem_arestas = "No valid edges found. Each step must include 'from' and 'to'."
        self.assertEqual(sem_arestas, self.texto(self.t.render_flowchart([], mode="text")))
        self.assertEqual(
            sem_arestas,
            self.texto(
                self.t.render_flowchart([{"to": "B"}, {"from": "A"}, {"from": "  ", "to": "C"}], mode="text")
            ),
        )
        for entrada in (None, {"a": 1}, "texto", 5, True):
            with self.subTest(entrada=entrada):
                self.assertEqual(
                    "Invalid 'steps': expected a list of objects.",
                    self.texto(self.t.render_flowchart(entrada, mode="text")),
                )
        self.assertEqual(
            "Invalid step at index 1: expected dict, got int.",
            self.texto(self.t.render_flowchart([{"from": "A", "to": "B"}, 7], mode="text")),
        )

    def test_direction_invalida_e_html_escapado(self):
        saida = self.texto(self.t.render_flowchart([{"from": "A", "to": "B"}], direction="zzz", mode="text"))
        self.assertIn("[A] --> [B]", saida)
        pagina = _texto(
            self.render(
                self.t.render_flowchart([{"from": "<b>", "to": "</b>", "label": "x&y"}], mode="embed")
            )
        )
        self.assertNotIn("<b>", pagina)
        self.assertIn("&lt;b&gt;", pagina)
        self.assertIn("&amp;", pagina)

    def test_labels_unicode_e_muito_longos(self):
        saida = self.texto(
            self.t.render_flowchart([{"from": "🚀", "to": "ç" * 500, "label": "ünïcødé"}], mode="text")
        )
        self.assertIn("🚀", saida)
        self.assertIn("ünïcødé", saida)
        self.assertIn("ç" * 500, saida)


# ============================================================
# render_tree
# ============================================================


class CasoRenderTree(CasoVisual):
    def test_dict_aninhado_saida_exata(self):
        self.assertEqual(
            "### Tree\n\n```text\nroot\n└─ a\n   └─ b\n      1\n```",
            self.texto(self.t.render_tree({"a": {"b": 1}}, mode="text")),
        )
        ramos = self.texto(self.t.render_tree({"a": {"b": 1, "c": 2}}, mode="text"))
        self.assertIn("├─ b", ramos)
        self.assertIn("└─ c", ramos)

    def test_edges_raiz_ordem_e_duplicados(self):
        self.assertEqual(
            "### Tree\n\n```text\np\n└─ c\n```",
            self.texto(self.t.render_tree([{"parent": "p", "child": "c"}], mode="text")),
        )
        self.assertEqual(
            "### Tree\n\n```text\nINICIO\n```",
            self.texto(self.t.render_tree([], root_label="INICIO", mode="text")),
        )
        self.assertEqual(
            "### Tree\n\n```text\nA\n├─ B\n└─ B\n```",
            self.texto(
                self.t.render_tree(
                    [{"parent": "A", "child": "B"}, {"parent": "A", "child": "B"}], mode="text"
                )
            ),
        )
        self.assertIn("root", self.texto(self.t.render_tree([{"foo": 1}], mode="text")))

    def test_max_depth_limites_e_arvore_profunda(self):
        profundo = {"a": {"b": {"c": 1}}}
        self.assertEqual(
            self.texto(self.t.render_tree(profundo, max_depth=1, mode="text")),
            self.texto(self.t.render_tree(profundo, max_depth=0, mode="text")),
        )
        self.assertIn("…", self.texto(self.t.render_tree(profundo, max_depth=1, mode="text")))
        arvore = {}
        atual = arvore
        for _ in range(80):
            novo = {}
            atual["a"] = novo
            atual = novo
        atual["fim"] = 1
        com_999 = self.texto(self.t.render_tree(arvore, max_depth=999, mode="text"))
        com_50 = self.texto(self.t.render_tree(arvore, max_depth=50, mode="text"))
        self.assertEqual(com_999, com_50)
        self.assertLess(len(com_999.split("\n")), 200)

    def test_ciclos_terminam_por_limite_de_profundidade(self):
        arestas = [
            {"parent": "root", "child": "A"},
            {"parent": "A", "child": "B"},
            {"parent": "B", "child": "A"},
        ]
        saida = self.texto(self.t.render_tree(arestas, mode="text"))
        self.assertTrue(saida.startswith("### Tree"))
        self.assertIn("…", saida)
        self.assertLess(len(saida.split("\n")), 30)
        ciclo_puro = self.texto(
            self.t.render_tree([{"parent": "A", "child": "B"}, {"parent": "B", "child": "A"}], mode="text")
        )
        self.assertIn("root", ciclo_puro)

    def test_entradas_invalidas(self):
        mensagem = (
            "Invalid 'tree': expected a dict (nested) or a list of {parent, child} edges."
        )
        for entrada in ("texto", None, 42, [1], ["a", "b"], True, 3.14):
            with self.subTest(entrada=entrada):
                self.assertEqual(mensagem, self.texto(self.t.render_tree(entrada, mode="text")))
        self.assertEqual(
            "Invalid edge at index 1: expected dict, got int.",
            self.texto(self.t.render_tree([{"parent": "a", "child": "b"}, 5], mode="text")),
        )

    def test_html_escapa_injecao_e_modo_texto(self):
        resposta = self.render(
            self.t.render_tree(
                {"</pre><script>alert(1)</script>": {"x": "<b>&"}},
                title="</title><script>alert(2)</script>",
                mode="embed",
            )
        )
        self.assertIsInstance(resposta, HTMLResponse)
        pagina = _texto(resposta)
        self.assertNotIn("<script>alert", pagina)
        self.assertEqual(1, pagina.count("</pre>"))
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", pagina)
        self.assertEqual(1, pagina.count("<title>"))
        self.assertIn("&lt;/title&gt;", pagina)
        self.assertTrue(
            self.texto(self.t.render_tree({"a": 1}, mode="text")).startswith("### Tree\n\n```text")
        )


# ============================================================
# Contrato geral (pureza, limites, ausencia de excepcoes)
# ============================================================


class CasoContratoGeral(CasoVisual):
    def test_valves_padrao_e_validacao_de_tipos(self):
        valves = Tools.Valves()
        self.assertEqual(250, valves.max_rows)
        self.assertEqual(60, valves.max_cols)
        self.assertEqual(12, valves.ascii_chart_height)
        self.assertEqual(420, valves.embed_chart_height)
        self.assertEqual("100%", valves.embed_chart_width)
        self.assertTrue(valves.allow_external_cdn)
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            Tools.Valves(max_rows="muitas")

    def test_modo_auto_depende_do_cdn_e_do_modo_explicito(self):
        self.t.valves.allow_external_cdn = False
        self.assertIsInstance(self.render(self.t.render_table([{"a": 1}], mode="auto")), str)
        self.assertIsInstance(self.render(self.t.render_chart(["a"], [1], mode="auto")), str)
        self.t.valves.allow_external_cdn = True
        self.assertIsInstance(self.render(self.t.render_table([{"a": 1}], mode="auto")), HTMLResponse)
        self.assertIsInstance(self.render(self.t.render_chart(["a"], [1], mode="auto")), HTMLResponse)
        self.assertIsInstance(self.render(self.t.render_table([{"a": 1}], mode="text")), str)

    def test_altura_ascii_dos_valves_e_respeitada(self):
        self.t.valves.ascii_chart_height = 20
        self.assertEqual(
            20, _linhas_eixo(self.texto(self.t.render_chart(["a", "b"], [1, 2], mode="text")))
        )
        self.t.valves.ascii_chart_height = 5
        self.assertEqual(
            5, _linhas_eixo(self.texto(self.t.render_chart(["a", "b"], [1, 2], mode="text")))
        )

    def test_todas_as_ferramentas_funcionam_sem_rede(self):
        # O event loop e criado ANTES de sem_rede(): no Windows o proactor loop
        # cria um self-pipe com socketpair() e sem_rede() bloqueia esse connect.
        loop = asyncio.new_event_loop()
        try:
            with sem_rede():
                resultados = [
                    loop.run_until_complete(self.t.render_table([{"a": 1}], mode="text")),
                    loop.run_until_complete(self.t.render_table([{"a": 1}], mode="embed")),
                    loop.run_until_complete(
                        self.t.render_comparison_table(["A"], ["c"], {"A": {"c": 1}}, mode="text")
                    ),
                    loop.run_until_complete(
                        self.t.render_comparison_table(["A"], ["c"], {"A": {"c": 1}}, mode="embed")
                    ),
                    loop.run_until_complete(self.t.render_chart(["a"], [1], mode="text")),
                    loop.run_until_complete(self.t.render_chart(["a"], [1], mode="embed")),
                    loop.run_until_complete(
                        self.t.render_multi_chart([{"name": "A", "x": ["a"], "y": [1]}], mode="text")
                    ),
                    loop.run_until_complete(
                        self.t.render_multi_chart([{"name": "A", "x": ["a"], "y": [1]}], mode="embed")
                    ),
                    loop.run_until_complete(self.t.render_line_chart(["a"], [1])),
                    loop.run_until_complete(self.t.render_bar_chart(["a"], [1])),
                    loop.run_until_complete(self.t.render_heatmap([[1]], ["r"], ["c"], mode="text")),
                    loop.run_until_complete(self.t.render_heatmap([[1]], ["r"], ["c"], mode="embed")),
                    loop.run_until_complete(self.t.render_timeline([{"label": "a"}], mode="text")),
                    loop.run_until_complete(self.t.render_timeline([{"label": "a"}], mode="embed")),
                    loop.run_until_complete(
                        self.t.render_flowchart([{"from": "A", "to": "B"}], mode="text")
                    ),
                    loop.run_until_complete(
                        self.t.render_flowchart([{"from": "A", "to": "B"}], mode="embed")
                    ),
                    loop.run_until_complete(self.t.render_tree({"a": 1}, mode="text")),
                    loop.run_until_complete(self.t.render_tree({"a": 1}, mode="embed")),
                ]
        finally:
            loop.close()
        for resultado in resultados:
            self.assertIsInstance(resultado, (str, HTMLResponse))
            self.assertTrue(_texto(resultado))

    def test_entradas_degeneradas_em_todas_as_ferramentas_sem_excecao(self):
        degenerados = [
            None,
            [],
            {},
            "",
            0,
            -1,
            3.14,
            True,
            "texto",
            "[]",
            "{}",
            "🚀",
            "ç" * 5000,
            [None],
            [{}],
            [[]],
            {"a": None},
            [1, 2],
            [{"a": 1}, "x"],
        ]
        falhas = []
        for valor in degenerados:
            chamadas = [
                ("render_table", lambda v=valor: self.t.render_table(v, mode="text")),
                ("render_table_embed", lambda v=valor: self.t.render_table(v, mode="embed")),
                ("render_comparison", lambda v=valor: self.t.render_comparison_table(v, v, v, mode="text")),
                ("render_chart", lambda v=valor: self.t.render_chart(v, v, mode="text")),
                ("render_multi_chart", lambda v=valor: self.t.render_multi_chart(v, mode="text")),
                ("render_line_chart", lambda v=valor: self.t.render_line_chart(v, v, height=5)),
                ("render_bar_chart", lambda v=valor: self.t.render_bar_chart(v, v, height=5)),
                ("render_heatmap", lambda v=valor: self.t.render_heatmap(v, v, v, mode="text")),
                ("render_timeline", lambda v=valor: self.t.render_timeline(v, mode="text")),
                ("render_flowchart", lambda v=valor: self.t.render_flowchart(v, mode="text")),
                ("render_tree", lambda v=valor: self.t.render_tree(v, mode="text")),
            ]
            for nome, chamada in chamadas:
                try:
                    saida = self.render(chamada())
                    if not _texto(saida):
                        falhas.append(f"{nome}({valor!r}) devolveu vazio")
                except Exception as exc:  # noqa: BLE001
                    falhas.append(f"{nome}({valor!r}) -> {type(exc).__name__}: {exc}")
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))

    def test_titulo_muito_longo_em_todos_os_renderizadores(self):
        titulo = "T" * 20000
        chamadas = [
            ("render_table", lambda: self.t.render_table([{"a": 1}], title=titulo, mode="text")),
            ("render_table_embed", lambda: self.t.render_table([{"a": 1}], title=titulo, mode="embed")),
            ("render_comparison", lambda: self.t.render_comparison_table(["A"], ["c"], {"A": {"c": 1}}, title=titulo, mode="text")),
            ("render_chart", lambda: self.t.render_chart(["a"], [1], title=titulo, mode="text")),
            ("render_chart_embed", lambda: self.t.render_chart(["a"], [1], title=titulo, mode="embed")),
            ("render_multi_chart", lambda: self.t.render_multi_chart([{"name": "s", "x": ["a"], "y": [1]}], title=titulo, mode="text")),
            ("render_heatmap", lambda: self.t.render_heatmap([[1]], ["r"], ["c"], title=titulo, mode="text")),
            ("render_timeline", lambda: self.t.render_timeline([{"label": "a"}], title=titulo, mode="text")),
            ("render_flowchart", lambda: self.t.render_flowchart([{"from": "A", "to": "B"}], title=titulo, mode="text")),
            ("render_tree", lambda: self.t.render_tree({"a": 1}, title=titulo, mode="text")),
        ]
        falhas = self._excecoes(chamadas)
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))
        for _, chamada in chamadas:
            self.assertGreater(len(self.texto(chamada())), 20000)

    def test_erro_nunca_e_htmlresponse_nem_500(self):
        # Entradas invalidas continuam a devolver texto simples (nunca HTMLResponse
        # com erro nem excepcao).
        erros = [
            self.render(self.t.render_table([], mode="embed")),
            self.render(self.t.render_chart({"a": 1}, [1], mode="embed")),
            self.render(self.t.render_tree("texto", mode="embed")),
            self.render(self.t.render_timeline(None, mode="embed")),
            self.render(self.t.render_heatmap("x", [], [], mode="embed")),
            self.render(self.t.render_flowchart([], mode="embed")),
            self.render(self.t.render_multi_chart([], mode="embed")),
        ]
        for resultado in erros:
            self.assertIsInstance(resultado, str)
            self.assertTrue(resultado)
            self.assertNotIn("Traceback", resultado)


# ============================================================
# Bugs de producao (nao corrigidos - documentados como expectedFailure)
# ============================================================


class CasoBugsConhecidos(CasoVisual):
    """Cada teste aqui e um bug real de ``tools/visuals_core.py`` (nenhum foi corrigido)."""

    @unittest.expectedFailure
    def test_bug_embed_nao_escapa_script_tag_no_json_do_plotly(self):
        # BUG: render_chart/render_multi_chart/render_heatmap escrevem json.dumps()
        # cru dentro de <script>. json.dumps nao escapa '<', '>' nem '/', por isso
        # qualquer titulo/label com "</script><script>..." fecha o bloco <script>
        # do Plotly e injecta codigo executavel na pagina (XSS/HTML nao escapado).
        # O <title> e a tabela HTML sao escapados (html.escape), mas o payload do
        # script nao.
        payload = "</script><script>alert('xss')</script>"
        paginas = {
            "render_chart_titulo": self.render(
                self.t.render_chart(["a"], [1], title=payload, mode="embed")
            ),
            "render_chart_label": self.render(self.t.render_chart([payload], [1], mode="embed")),
            "render_multi_chart_label": self.render(
                self.t.render_multi_chart([{"name": payload, "x": ["a"], "y": [1]}], mode="embed")
            ),
            "render_heatmap_label": self.render(
                self.t.render_heatmap([[1]], [payload], [payload], mode="embed")
            ),
        }
        falhas = []
        for nome, resposta in paginas.items():
            pagina = _texto(resposta)
            posicao = pagina.find("<script>alert")
            if posicao != -1:
                falhas.append(f"{nome}: tag <script> injectada crua -> {pagina[max(0, posicao - 30):posicao + 50]!r}")
        self.assertEqual([], falhas, "HTML/SVG nao escapado: " + " | ".join(falhas))

    @unittest.expectedFailure
    def test_bug_nan_e_infinity_levam_a_valueerror(self):
        # BUG: json.loads aceita NaN/Infinity e float("nan") passa em _coerce_float_list,
        # mas _ascii_line_chart/_ascii_scatter_chart/_ascii_heatmap fazem int(nan)
        # -> ValueError ("cannot convert float NaN to integer") que escapa da ferramenta.
        casos = [
            ("render_chart_nan_json", lambda: self.t.render_chart(["a", "b"], "[1, NaN]", mode="text")),
            ("render_chart_infinity_json", lambda: self.t.render_chart(["a", "b"], "[1, Infinity]", mode="text")),
            ("render_chart_nan_python", lambda: self.t.render_chart(["a", "b"], [1.0, float("nan")], mode="text")),
            ("render_line_chart_nan", lambda: self.t.render_line_chart(["a", "b"], [1.0, float("nan")], height=5)),
            ("render_multi_chart_nan", lambda: self.t.render_multi_chart([{"name": "s", "x": ["a", "b"], "y": "[1, NaN]"}], mode="text")),
            ("render_heatmap_nan", lambda: self.t.render_heatmap("[[1, NaN]]", [], [], mode="text")),
            ("render_heatmap_infinity", lambda: self.t.render_heatmap("[[1, Infinity]]", [], [], mode="text")),
        ]
        falhas = self._excecoes(casos)
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))

    @unittest.expectedFailure
    def test_bug_inteiro_gigante_leva_a_overflowerror(self):
        # BUG: numeros inteiros maiores que float (ex.: 10**400, que json.loads
        # devolve como int sem problema) rebentam em float(x) dentro de
        # _coerce_float_list/_find_best_values/heatmap -> OverflowError nao tratado.
        gigante = 10 ** 400
        casos = [
            ("render_chart", lambda: self.t.render_chart(["a"], [gigante], mode="text")),
            ("render_line_chart", lambda: self.t.render_line_chart(["a"], [gigante], height=5)),
            ("render_bar_chart", lambda: self.t.render_bar_chart(["a"], [gigante], height=5)),
            ("render_heatmap", lambda: self.t.render_heatmap([[gigante]], ["r"], ["c"], mode="text")),
            ("render_comparison_table", lambda: self.t.render_comparison_table(["A"], ["s"], {"A": {"s": gigante}}, mode="text")),
            ("render_chart_string_json", lambda: self.t.render_chart(["a"], "[" + "9" * 400 + "]", mode="text")),
        ]
        falhas = self._excecoes(casos)
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))

    @unittest.expectedFailure
    def test_bug_tipos_invalidos_em_height_e_max_depth_levantam(self):
        # BUG: int(height) e int(max_depth) sao chamados sem try. Um argumento JSON
        # com tipo errado (string nao numerica, None, lista) escapa como
        # ValueError/TypeError em vez de devolver a mensagem de erro do projecto.
        casos = [
            ("line_chart_height_str", lambda: self.t.render_line_chart(["a"], [1], height="abc")),
            ("line_chart_height_none", lambda: self.t.render_line_chart(["a"], [1], height=None)),
            ("line_chart_height_lista", lambda: self.t.render_line_chart(["a"], [1], height=[5])),
            ("bar_chart_height_str", lambda: self.t.render_bar_chart(["a"], [1], height="abc")),
            ("tree_max_depth_str", lambda: self.t.render_tree({"a": 1}, max_depth="abc")),
            ("tree_max_depth_none", lambda: self.t.render_tree({"a": 1}, max_depth=None)),
        ]
        falhas = self._excecoes(casos)
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))

    @unittest.expectedFailure
    def test_bug_ascii_chart_height_zero_levanta_indexerror(self):
        # BUG: Tools.Valves nao valida ascii_chart_height (falta ge=1). Com 0 ou
        # negativo, _ascii_line_chart/_ascii_scatter_chart criam um grid vazio
        # (height=0) e fazem grid[row][col] -> IndexError.
        self.t.valves.ascii_chart_height = 0
        casos = [
            ("render_chart_line", lambda: self.t.render_chart(["a"], [1], mode="text")),
            ("render_chart_scatter", lambda: self.t.render_chart(["a"], [1], chart_type="scatter", mode="text")),
            ("render_multi_chart", lambda: self.t.render_multi_chart([{"name": "s", "x": ["a"], "y": [1]}], mode="text")),
        ]
        falhas = self._excecoes(casos)
        self.t.valves.ascii_chart_height = -1
        falhas += self._excecoes(
            [("render_chart_line_negativo", lambda: self.t.render_chart(["a"], [1], mode="text"))]
        )
        self.assertEqual([], falhas, "excecoes escaparam: " + "; ".join(falhas))

    @unittest.expectedFailure
    def test_bug_chaves_nao_string_perdem_valores_na_tabela(self):
        # BUG: render_table cria o cabecalho com str(k) mas le a celula com
        # r.get(c) usando essa string. Com chaves nao-string (int, float, tuple)
        # o cabecalho aparece e o valor desaparece silenciosamente da tabela.
        saida = self.texto(self.t.render_table([{1: "valor-perdido", "b": 2}], mode="text"))
        self.assertIn("| 1 | b |", saida)
        self.assertIn("| valor-perdido | 2 |", saida)


if __name__ == "__main__":
    unittest.main()
