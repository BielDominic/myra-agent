# -*- coding: utf-8 -*-
"""Testes severos de ``tasks/structured_tools.py`` (FASE 24.2).

Cobre as seis ferramentas registradas por ``registrar_todas`` e os helpers de
parsing (``_post`` e ``_limpar_url_google``):

* ``search_google_structured`` -- monta a URL do Google, faz ``requests.get``
  DIRETO (linha 47) e parseia os hrefs ``/url?q=...`` com regex.
* ``web_search_structured`` -- faz ``requests.post`` DIRETO ao DuckDuckGo
  (linha 86), extrai ``result__a``/``result__snippet`` e desfaz o ``uddg=``.
* ``youtube_search`` / ``youtube_channel_latest`` -- usam o yt-dlp, aqui
  substituido por um modulo falso (o yt-dlp real nunca e importado).
* ``get_current_url`` / ``read_page_structured`` -- usam o helper ``_post``
  contra o backend local (sempre mockado).

Regras de seguranca aplicadas em TODOS os testes: ``sem_rede()`` activo (nenhum
socket), ``requests.get``/``requests.post``/``_post`` sempre substituidos por
dublês e o yt-dlp real nunca executado. Nenhum ficheiro e escrito.

Os testes marcados com ``@unittest.expectedFailure`` documentam bugs de
producao encontrados (prefixo ``BUG:`` no comentario) e reportados no relatorio.
"""
from __future__ import annotations

import json
import socket
import sys
import types
import unittest
import urllib.parse
import urllib.request
from unittest import mock

import requests

from tasks import structured_tools as st
from tests.helpers import CasoBase, eh_erro_estruturado, sem_rede

# ============================================================
# Dublês
# ============================================================

_SEM_JSON = object()


class RespostaFalsa:
    """Dublê minimo de ``requests.Response``.

    ``json_data`` ausente -> ``json()`` levanta ``ValueError`` (corpo HTML
    invalido, comportamento real de ``requests``). ``sem_text=True`` remove o
    atributo ``text`` (resposta corrompida).
    """

    def __init__(self, text="", status_code=200, json_data=_SEM_JSON,
                 json_erro=None, sem_text=False):
        if not sem_text:
            self.text = text
        self.status_code = status_code
        self._json_data = json_data
        self._json_erro = json_erro

    def json(self):
        if self._json_erro is not None:
            raise self._json_erro
        if self._json_data is _SEM_JSON:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error", response=self)

    @property
    def ok(self) -> bool:
        return self.status_code < 400


class _YoutubeDLFalso:
    """Objeto devolvido por ``YtDlpFalso.modulo.YoutubeDL(opts)``."""

    def __init__(self, dono: "YtDlpFalso", opts):
        self.dono = dono
        self.opts = dict(opts or {})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, target, download=False):
        self.dono.chamadas.append({
            "target": target,
            "download": download,
            "opts": self.opts,
        })
        if not self.dono.roteiro:
            raise AssertionError("yt_dlp chamado mais vezes do que o roteiro previa")
        item = self.dono.roteiro.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class YtDlpFalso:
    """Substitui o modulo ``yt_dlp`` inteiro dentro de ``with``.

    O roteiro e consumido em ordem: cada item e devolvido por ``extract_info``
    ou, se for uma excepcao, levantado.
    """

    def __init__(self, *roteiro):
        self.roteiro = list(roteiro)
        self.chamadas: list[dict] = []
        modulo = types.ModuleType("yt_dlp")
        modulo.__version__ = "falso"
        modulo.YoutubeDL = lambda opts=None: _YoutubeDLFalso(self, opts)
        self.modulo = modulo
        self._patch = None

    def __enter__(self) -> "YtDlpFalso":
        self._patch = mock.patch.dict(sys.modules, {"yt_dlp": self.modulo})
        self._patch.start()
        return self

    def __exit__(self, *exc) -> bool:
        self._patch.stop()
        return False

    @property
    def targets(self) -> list[str]:
        return [c["target"] for c in self.chamadas]


def modulo_yt_dlp_que_explode(erro: BaseException):
    """Modulo ``yt_dlp`` cujo construtor de ``YoutubeDL`` levanta sempre."""
    modulo = types.ModuleType("yt_dlp")
    modulo.__version__ = "falso"

    def _explode(opts=None):
        raise erro

    modulo.YoutubeDL = _explode
    return modulo


# ============================================================
# HTML de exemplo
# ============================================================

# href como o Google devolve (o '&' final faz parte de '&amp;sa=U' no HTML real)
LINK_GOOGLE = "/url?q=https%3A%2F%2Fexemplo.com%2Fpagina&amp;sa=U&amp;ved=2ahUKEwi"


def html_google(itens) -> str:
    """``itens``: lista de ``(href, titulo_html)``."""
    return "".join(
        f'<div class="g"><a href="{href}" data-ved="x"><h3 class="LC20lb">{titulo}</h3></a>'
        f'<div class="VwiC3b">texto do snippet nao e extraido</div></div>'
        for href, titulo in itens
    )


def link_google(url_bruta: str) -> str:
    """Monta um href ``/url?q=`` como o Google faz (percent-encoded)."""
    return "/url?q=" + urllib.parse.quote(url_bruta, safe="") + "&amp;sa=U&amp;ved=abc"


def html_ddg(itens) -> str:
    """``itens``: lista de ``(href, titulo, snippet)``."""
    return "".join(
        f'<div class="result"><a rel="nofollow" class="result__a" href="{href}">{titulo}</a>'
        f'<a class="result__snippet" href="{href}">{snippet}</a></div>'
        for href, titulo, snippet in itens
    )


# ============================================================
# Base: CasoBase + rede real bloqueada em todos os testes
# ============================================================

class CasoFerramentas(CasoBase):
    """``CasoBase`` (ambiente isolado) com ``sem_rede()`` sempre activo."""

    def setUp(self) -> None:
        super().setUp()
        self._bloqueio_rede = sem_rede()
        self._bloqueio_rede.__enter__()

    def tearDown(self) -> None:
        self._bloqueio_rede.__exit__(None, None, None)
        super().tearDown()

    # -- atalhos de mock ------------------------------------------------
    def patch_get(self, **kwargs):
        return mock.patch.object(st.requests, "get", **kwargs)

    def patch_post(self, **kwargs):
        return mock.patch.object(st.requests, "post", **kwargs)

    def patch_interno(self, **kwargs):
        return mock.patch.object(st, "_post", **kwargs)

    def assertErro(self, saida, trecho=None):
        """Verifica o formato de erro do projeto e (opcional) o texto."""
        self.assertIsInstance(saida, dict, f"esperava dict, veio {type(saida).__name__}")
        self.assertTrue(eh_erro_estruturado(saida), f"nao e erro estruturado: {saida!r}")
        self.assertIsInstance(saida.get("result"), str)
        if trecho is not None:
            self.assertIn(trecho, saida["result"])

    def assertOkLista(self, saida, quantidade):
        """Verifica o contrato de sucesso das ferramentas de busca."""
        self.assertEqual(saida["status"], "ok")
        self.assertEqual(saida["count"], quantidade)
        self.assertEqual(len(saida["results"]), quantidade)
        corpo = json.loads(saida["result"])
        self.assertEqual(corpo["count"], quantidade)
        self.assertEqual(len(corpo["results"]), quantidade)
        self.assertEqual(corpo["results"], saida["results"])


# ============================================================
# _post
# ============================================================

class TestHelperPost(CasoFerramentas):
    """Contrato de ``_post`` (unica ponte com o backend local)."""

    def test_post_monta_url_do_agent_envia_json_e_timeout(self):
        with self.patch_post(return_value=RespostaFalsa(json_data={"status": "ok", "url": "u"})) as falso:
            saida = st._post("/get_current_url", {"a": 1}, timeout=7)

        self.assertEqual(saida, {"status": "ok", "url": "u"})
        self.assertEqual(falso.call_args.args[0], st.AGENT_URL + "/get_current_url")
        self.assertEqual(falso.call_args.kwargs["json"], {"a": 1})
        self.assertEqual(falso.call_args.kwargs["timeout"], 7)

    def test_post_timeout_padrao_e_60_segundos(self):
        with self.patch_post(return_value=RespostaFalsa(json_data={"status": "ok"})) as falso:
            st._post("/x", {})
        self.assertEqual(falso.call_args.kwargs["timeout"], 60)

    def test_post_usa_a_base_do_backend_local(self):
        self.assertEqual(st.AGENT_URL, "http://127.0.0.1:8000")

    def test_post_json_invalido_devolve_erro_estruturado(self):
        with self.patch_post(return_value=RespostaFalsa(text="<html>nao e json</html>")):
            saida = st._post("/x", {})
        self.assertErro(saida, "ValueError")

    def test_post_jsondecodeerror_do_requests_e_apanhado(self):
        efeito = requests.exceptions.JSONDecodeError("Expecting value", "<html>", 0)
        with self.patch_post(return_value=RespostaFalsa(json_erro=efeito)):
            saida = st._post("/x", {})
        self.assertErro(saida, "JSONDecodeError")

    def test_post_timeout_devolve_erro_em_vez_de_levantar(self):
        with self.patch_post(side_effect=requests.exceptions.Timeout("estourou")):
            saida = st._post("/x", {})
        self.assertErro(saida, "Timeout")

    def test_post_conexao_recusada_devolve_erro(self):
        with self.patch_post(side_effect=requests.exceptions.ConnectionError("recusada")):
            saida = st._post("/x", {})
        self.assertErro(saida, "ConnectionError")

    def test_post_devolve_payload_nao_dict_sem_validar(self):
        # Documenta que _post nao valida o JSON devolvido: o consumidor trata.
        for payload in (["a"], "texto", 42, None):
            with self.subTest(payload=payload):
                with self.patch_post(return_value=RespostaFalsa(json_data=payload)):
                    self.assertEqual(st._post("/x", {}), payload)

    def test_post_nao_apanha_baseexception(self):
        # Apanha apenas Exception: um BaseException do transporte propaga.
        with self.patch_post(side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                st._post("/x", {})


# ============================================================
# _limpar_url_google
# ============================================================

class TestLimparUrlGoogle(CasoFerramentas):

    def test_url_sem_redirect_e_devolvida_igual(self):
        url = "https://exemplo.com/pagina?x=1"
        self.assertEqual(st._limpar_url_google(url), url)

    def test_extrai_parametro_q_percent_decodificado(self):
        self.assertEqual(
            st._limpar_url_google("https://www.google.com/url?q=https%3A%2F%2Fa.com%2Fx%3Fy%3D1%26z%3D2"),
            "https://a.com/x?y=1&z=2",
        )

    def test_ignora_parametros_extra_do_google(self):
        self.assertEqual(
            st._limpar_url_google("https://www.google.com/url?q=https%3A%2F%2Fa.com%2F&sa=U&ved=1"),
            "https://a.com/",
        )

    def test_q_vazio_devolve_url_original(self):
        url = "https://www.google.com/url?q="
        self.assertEqual(st._limpar_url_google(url), url)

    def test_string_vazia_nao_levanta(self):
        self.assertEqual(st._limpar_url_google(""), "")

    def test_unicode_percent_decodificado(self):
        self.assertEqual(
            st._limpar_url_google("https://www.google.com/url?q=https%3A%2F%2Fa.com%2Fcaf%C3%A9"),
            "https://a.com/caf\u00e9",
        )

    def test_url_relativa_sem_esquema(self):
        self.assertEqual(
            st._limpar_url_google("/url?q=https%3A%2F%2Fa.com"),
            "https://a.com",
        )

    def test_varios_parametros_q_usa_o_primeiro(self):
        self.assertEqual(
            st._limpar_url_google("https://www.google.com/url?q=primeiro&q=segundo"),
            "primeiro",
        )


# ============================================================
# search_google_structured
# ============================================================

class TestSearchGoogleStructured(CasoFerramentas):

    # -- contrato de sucesso -------------------------------------------
    def test_sucesso_dois_resultados_com_contrato_completo(self):
        html = html_google([
            (link_google("https://exemplo.com/um"), "Titulo Um"),
            (link_google("https://exemplo.com/dois"), "Titulo Dois"),
        ])
        with self.patch_get(return_value=RespostaFalsa(text=html)) as falso:
            saida = st.search_google_structured("termo", 5)

        self.assertOkLista(saida, 2)
        self.assertEqual(saida["results"][0], {
            "titulo": "Titulo Um", "url": "https://exemplo.com/um", "snippet": "",
        })
        self.assertEqual(saida["results"][1]["url"], "https://exemplo.com/dois")
        falso.assert_called_once()

    def test_url_da_requisicao_headers_e_timeout(self):
        with self.patch_get(return_value=RespostaFalsa(text=html_google([(LINK_GOOGLE, "T")]))) as falso:
            st.search_google_structured("caf\u00e9 da manh\u00e3", 5)

        url = falso.call_args.args[0]
        self.assertEqual(
            url,
            "https://www.google.com/search?q=" + urllib.parse.quote("caf\u00e9 da manh\u00e3") + "&num=5",
        )
        cabecalhos = falso.call_args.kwargs["headers"]
        self.assertIn("Mozilla/5.0", cabecalhos["User-Agent"])
        self.assertEqual(cabecalhos["Accept-Language"], "pt-BR,pt;q=0.9,en;q=0.8")
        self.assertEqual(falso.call_args.kwargs["timeout"], 30)

    def test_titulo_recebe_limpeza_de_tags_e_entidades(self):
        html = html_google([(LINK_GOOGLE, "A <b>B</b> &amp; C &#39;d&#39; &quot;e&quot;")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertEqual(saida["results"][0]["titulo"], 'A B & C \'d\' "e"')

    def test_titulo_so_com_espacos_fica_vazio(self):
        html = html_google([(LINK_GOOGLE, "   ")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertEqual(saida["results"][0]["titulo"], "")

    def test_snippet_e_sempre_vazio_por_design(self):
        html = html_google([(LINK_GOOGLE, "T")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertEqual(saida["results"][0]["snippet"], "")

    def test_links_duplicados_nao_sao_deduplicados(self):
        html = html_google([(LINK_GOOGLE, "A"), (LINK_GOOGLE, "B")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertOkLista(saida, 2)

    # -- limites de max_resultados -------------------------------------
    def test_max_resultados_limita_a_lista(self):
        html = html_google([(link_google(f"https://a.com/{i}"), f"T{i}") for i in range(5)])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 2)
        self.assertOkLista(saida, 2)
        self.assertEqual([r["url"] for r in saida["results"]], ["https://a.com/0", "https://a.com/1"])

    def test_max_resultados_maior_que_o_disponivel(self):
        html = html_google([(link_google(f"https://a.com/{i}"), f"T{i}") for i in range(3)])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 50)
        self.assertOkLista(saida, 3)

    def test_max_resultados_zero_devolve_erro(self):
        # Documenta: max_resultados=0 nao devolve lista vazia com status ok --
        # devolve erro com a mensagem generica de "possivel bloqueio".
        html = html_google([(LINK_GOOGLE, "T")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 0)
        self.assertErro(saida, "possivel bloqueio")

    def test_max_resultados_negativo_devolve_erro(self):
        html = html_google([(LINK_GOOGLE, "T")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", -3)
        self.assertErro(saida)

    def test_max_resultados_tipo_errado_devolve_erro(self):
        html = html_google([(LINK_GOOGLE, "T")])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", "3")
        self.assertErro(saida, "TypeError")

    def test_max_resultados_10000_e_1000_resultados_no_html(self):
        html = html_google([(link_google(f"https://a.com/{i}"), f"T{i}") for i in range(1000)])
        with self.patch_get(return_value=RespostaFalsa(text=html)) as falso:
            saida = st.search_google_structured("q", 10000)
        self.assertIn("&num=10000", falso.call_args.args[0])
        self.assertOkLista(saida, 1000)

    # -- query: vazia, tipos errados, unicode, perigosos ----------------
    def test_query_vazia_devolve_erro_sem_tocar_na_rede(self):
        with self.patch_get() as falso:
            saida = st.search_google_structured("", 5)
        self.assertErro(saida, "query")
        falso.assert_not_called()

    def test_query_none_devolve_erro_sem_tocar_na_rede(self):
        with self.patch_get() as falso:
            saida = st.search_google_structured(None, 5)
        self.assertErro(saida, "query")
        falso.assert_not_called()

    def test_query_inteiro_devolve_erro_estruturado(self):
        with self.patch_get(return_value=RespostaFalsa(text="")) as falso:
            saida = st.search_google_structured(123, 5)
        self.assertErro(saida, "TypeError")
        falso.assert_not_called()

    def test_query_lista_devolve_erro_estruturado(self):
        with self.patch_get(return_value=RespostaFalsa(text="")):
            saida = st.search_google_structured(["a", "b"], 5)
        self.assertErro(saida, "TypeError")

    def test_query_so_espacos_e_aceite_e_percent_encoded(self):
        with self.patch_get(return_value=RespostaFalsa(text=html_google([(LINK_GOOGLE, "T")]))) as falso:
            saida = st.search_google_structured("   ", 5)
        self.assertIn("q=%20%20%20&num=5", falso.call_args.args[0])
        self.assertEqual(saida["status"], "ok")

    def test_query_unicode_emoji_percent_encoded_no_url(self):
        termo = "caf\u00e9 \U0001f600 busca"
        with self.patch_get(return_value=RespostaFalsa(text=html_google([(LINK_GOOGLE, "T")]))) as falso:
            saida = st.search_google_structured(termo, 5)
        self.assertEqual(
            falso.call_args.args[0],
            "https://www.google.com/search?q=" + urllib.parse.quote(termo) + "&num=5",
        )
        self.assertNotIn("\U0001f600", falso.call_args.args[0])
        self.assertEqual(saida["status"], "ok")

    def test_query_com_caracteres_perigosos_e_escapada(self):
        termo = '"&<script>alert(1)</script> \' onmouseover=x'
        with self.patch_get(return_value=RespostaFalsa(text=html_google([(LINK_GOOGLE, "T")]))) as falso:
            st.search_google_structured(termo, 5)
        url = falso.call_args.args[0]
        for perigoso in ('"', "<", ">"):
            self.assertNotIn(perigoso, url)
        self.assertNotIn("<script>", url)

    # -- respostas HTTP hostis -----------------------------------------
    def test_http500_com_html_vazio_devolve_erro_sem_propagar_status(self):
        with self.patch_get(return_value=RespostaFalsa(text="", status_code=500)):
            saida = st.search_google_structured("q", 5)
        self.assertErro(saida, "parseaveis")

    def test_http403_pagina_de_captcha_devolve_erro(self):
        with self.patch_get(return_value=RespostaFalsa(text="<html>captcha</html>", status_code=403)):
            saida = st.search_google_structured("q", 5)
        self.assertErro(saida, "parseaveis")

    def test_http500_com_markup_valido_nao_e_verificado(self):
        # Documenta: a ferramenta nunca chama raise_for_status()/le status_code,
        # por isso um 500 com markup parecido e devolvido como sucesso.
        html = html_google([(LINK_GOOGLE, "T")])
        with self.patch_get(return_value=RespostaFalsa(text=html, status_code=500)):
            saida = st.search_google_structured("q", 5)
        self.assertEqual(saida["status"], "ok")

    def test_html_vazio_devolve_erro(self):
        with self.patch_get(return_value=RespostaFalsa(text="")):
            self.assertErro(st.search_google_structured("q", 5), "parseaveis")

    def test_html_malformado_nao_levanta(self):
        for html in (
            '<a href="/url?q=abc"><h3>sem fechar<div><span',
            '<a href="/url?q=" ><h3></h3></a>',
            "><<>>>&&&;;;",
            "<h3>Titulo</h3>",
        ):
            with self.subTest(html=html):
                with self.patch_get(return_value=RespostaFalsa(text=html)):
                    saida = st.search_google_structured("q", 5)
                self.assertErro(saida, "parseaveis")

    def test_href_sem_aspas_nao_e_parseado(self):
        with self.patch_get(return_value=RespostaFalsa(text='<a href=/url?q=https://a.com&x><h3>T</h3></a>')):
            self.assertErro(st.search_google_structured("q", 5))

    def test_href_com_aspas_simples_nao_e_parseado(self):
        with self.patch_get(return_value=RespostaFalsa(text="<a href='/url?q=x'><h3>T</h3></a>")):
            self.assertErro(st.search_google_structured("q", 5))

    def test_markup_dentro_de_script_e_extraido_sem_filtragem(self):
        # Documenta: o parser nao remove <script>; markup dentro de JavaScript
        # tambem vira "resultado", logo o conteudo da pagina nunca pode ser
        # tratado como confiavel.
        html = ('<script>var s = \'<a href="/url?q=https%3A%2F%2Fmalicioso.com%2F">'
                '<h3>Injetado</h3></a>\';</script>' + html_google([(LINK_GOOGLE, "Legitimo")]))
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertOkLista(saida, 2)
        self.assertEqual(saida["results"][0]["url"], "https://malicioso.com/")
        self.assertEqual(saida["results"][0]["titulo"], "Injetado")

    def test_resposta_com_text_none_devolve_erro(self):
        with self.patch_get(return_value=RespostaFalsa(text=None)):
            self.assertErro(st.search_google_structured("q", 5), "TypeError")

    def test_resposta_com_text_bytes_devolve_erro(self):
        with self.patch_get(return_value=RespostaFalsa(text=b"<a href='/url?q=x'><h3>T</h3></a>")):
            self.assertErro(st.search_google_structured("q", 5), "TypeError")

    def test_resposta_sem_atributo_text_devolve_erro(self):
        with self.patch_get(return_value=RespostaFalsa(sem_text=True)):
            self.assertErro(st.search_google_structured("q", 5), "AttributeError")

    def test_excecoes_do_transporte_nao_escapam(self):
        excecoes = [
            requests.exceptions.Timeout("t"),
            requests.exceptions.ConnectionError("c"),
            requests.exceptions.SSLError("s"),
            requests.exceptions.TooManyRedirects("r"),
            OSError("rede bloqueada nos testes do MYRA"),
            ValueError("v"),
            RuntimeError("r"),
            KeyError("k"),
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "z"),
        ]
        for erro in excecoes:
            with self.subTest(erro=type(erro).__name__):
                with self.patch_get(side_effect=erro):
                    saida = st.search_google_structured("q", 5)
                self.assertErro(saida)
                self.assertIn(type(erro).__name__, saida["result"])

    @unittest.expectedFailure
    def test_bug_url_com_query_string_e_truncada(self):
        # BUG: search_google_structured faz urllib.parse.unquote() ANTES de
        # _limpar_url_google() (linhas 55-56). Com isso o '&' interno da URL de
        # destino (que vinha como %26) passa a ser separador de query e todo o
        # resto da URL e perdido. _limpar_url_google sozinho trata bem o caso
        # (ver TestLimparUrlGoogle.test_extrai_parametro_q_percent_decodificado).
        html = html_google([
            (link_google("https://exemplo.com/pag?id=1&x=2"), "Com parametros"),
        ])
        with self.patch_get(return_value=RespostaFalsa(text=html)):
            saida = st.search_google_structured("q", 5)
        self.assertEqual(saida["results"][0]["url"], "https://exemplo.com/pag?id=1&x=2")


# ============================================================
# web_search_structured
# ============================================================

class TestWebSearchStructured(CasoFerramentas):

    def test_sucesso_dois_resultados_com_contrato_completo(self):
        html = html_ddg([
            ("https://a.com/1", "Titulo Um", "Snippet um"),
            ("https://a.com/2", "Titulo Dois", "Snippet dois"),
        ])
        with self.patch_post(return_value=RespostaFalsa(text=html)) as falso:
            saida = st.web_search_structured("termo", 5)

        self.assertOkLista(saida, 2)
        self.assertEqual(saida["results"][0], {
            "titulo": "Titulo Um", "url": "https://a.com/1", "snippet": "Snippet um",
        })
        self.assertEqual(falso.call_args.args[0], "https://html.duckduckgo.com/html/")
        self.assertEqual(falso.call_args.kwargs["data"], {"q": "termo"})
        self.assertEqual(
            falso.call_args.kwargs["headers"]["Content-Type"],
            "application/x-www-form-urlencoded",
        )
        self.assertEqual(falso.call_args.kwargs["timeout"], 30)

    def test_query_unicode_emoji_perigosa_vai_intacta_no_payload(self):
        termo = 'caf\u00e9 \U0001f600 "&<script>'
        html = html_ddg([("https://a.com", "T", "S")])
        with self.patch_post(return_value=RespostaFalsa(text=html)) as falso:
            saida = st.web_search_structured(termo, 5)
        self.assertEqual(falso.call_args.kwargs["data"], {"q": termo})
        self.assertEqual(saida["results"][0]["titulo"], "T")

    def test_max_resultados_limita_a_lista(self):
        html = html_ddg([(f"https://a.com/{i}", f"T{i}", f"S{i}") for i in range(5)])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 2)
        self.assertOkLista(saida, 2)
        self.assertEqual([r["url"] for r in saida["results"]], ["https://a.com/0", "https://a.com/1"])

    def test_max_resultados_maior_que_o_disponivel(self):
        html = html_ddg([(f"https://a.com/{i}", f"T{i}", f"S{i}") for i in range(3)])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            self.assertOkLista(st.web_search_structured("q", 100), 3)

    def test_max_resultados_zero_e_negativo_devolvem_erro(self):
        html = html_ddg([("https://a.com", "T", "S")])
        for limite in (0, -1, -100):
            with self.subTest(limite=limite):
                with self.patch_post(return_value=RespostaFalsa(text=html)):
                    saida = st.web_search_structured("q", limite)
                self.assertErro(saida)

    def test_max_resultados_tipo_errado_devolve_erro(self):
        html = html_ddg([("https://a.com", "T", "S")])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", "2")
        self.assertErro(saida, "TypeError")

    def test_max_resultados_10000_com_1000_resultados(self):
        html = html_ddg([(f"https://a.com/{i}", f"T{i}", f"S{i}") for i in range(1000)])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            self.assertOkLista(st.web_search_structured("q", 10000), 1000)

    def test_uddg_relativo_e_decodificado(self):
        link = "//duckduckgo.com/l/?uddg=https%3A%2F%2Freal.com%2Fp%3Fa%3D1%26b%3D2&rut=x"
        html = html_ddg([(link, "T", "S")])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(saida["results"][0]["url"], "https://real.com/p?a=1&b=2")

    def test_link_sem_uddg_e_mantido(self):
        html = html_ddg([("https://direto.com/pagina", "T", "S")])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(saida["results"][0]["url"], "https://direto.com/pagina")

    def test_entidades_limpas_em_titulo_e_snippet(self):
        html = html_ddg([("https://a.com", "A &amp; B &#x27;c&#x27; &quot;d&quot;", "S &amp; &#x27;x&#x27;")])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(saida["results"][0]["titulo"], 'A & B \'c\' "d"')
        self.assertEqual(saida["results"][0]["snippet"], "S & 'x'")

    def test_tags_html_sao_removidas(self):
        html = html_ddg([("https://a.com", "T <b>forte</b>", "S <em>italico</em>")])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(saida["results"][0]["titulo"], "T forte")
        self.assertEqual(saida["results"][0]["snippet"], "S italico")

    def test_snippet_e_truncado_a_300_caracteres(self):
        html = html_ddg([("https://a.com", "T", "x" * 500)])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(len(saida["results"][0]["snippet"]), 300)

    def test_snippet_com_unicode_e_truncado_por_caracteres(self):
        html = html_ddg([("https://a.com", "T", "\U0001f600" * 400)])
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            saida = st.web_search_structured("q", 5)
        self.assertEqual(len(saida["results"][0]["snippet"]), 300)
        self.assertEqual(saida["results"][0]["snippet"], "\U0001f600" * 300)

    def test_href_antes_da_class_nao_e_parseado(self):
        # Documenta a fragilidade da regex: exige class="result__a" ANTES de href.
        html = '<a href="https://a.com" class="result__a">T</a><a class="result__snippet">S</a>'
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            self.assertErro(st.web_search_structured("q", 5))

    def test_resultado_sem_snippet_nao_e_parseado(self):
        html = '<a class="result__a" href="https://a.com">T</a>'
        with self.patch_post(return_value=RespostaFalsa(text=html)):
            self.assertErro(st.web_search_structured("q", 5))

    def test_html_vazio_e_malformado_devolvem_erro(self):
        for html in ("", "   ", "<div><a class=", '<a class="result__a" href="><a class="result__snippet">'):
            with self.subTest(html=html):
                with self.patch_post(return_value=RespostaFalsa(text=html)):
                    self.assertErro(st.web_search_structured("q", 5), "DuckDuckGo")

    def test_query_vazia_ou_none_devolve_erro_sem_pedido(self):
        for termo in ("", None):
            with self.subTest(termo=termo):
                with self.patch_post() as falso:
                    saida = st.web_search_structured(termo, 5)
                self.assertErro(saida, "query")
                falso.assert_not_called()

    def test_http403_e_http500_devolvem_erro(self):
        for codigo, corpo in ((403, "<html>forbidden</html>"), (500, ""), (429, "rate limit")):
            with self.subTest(codigo=codigo):
                with self.patch_post(return_value=RespostaFalsa(text=corpo, status_code=codigo)):
                    self.assertErro(st.web_search_structured("q", 5))

    def test_respostas_corrompidas_devolvem_erro(self):
        casos = {
            "text_none": RespostaFalsa(text=None),
            "text_bytes": RespostaFalsa(text=b"<html>"),
            "sem_text": RespostaFalsa(sem_text=True),
            "sem_status": object(),
        }
        for nome, resposta in casos.items():
            with self.subTest(caso=nome):
                with self.patch_post(return_value=resposta):
                    self.assertErro(st.web_search_structured("q", 5))

    def test_excecoes_do_transporte_nao_escapam(self):
        excecoes = [
            requests.exceptions.Timeout("t"),
            requests.exceptions.ConnectionError("c"),
            requests.exceptions.ProxyError("p"),
            OSError("rede bloqueada nos testes do MYRA"),
            RuntimeError("r"),
        ]
        for erro in excecoes:
            with self.subTest(erro=type(erro).__name__):
                with self.patch_post(side_effect=erro):
                    saida = st.web_search_structured("q", 5)
                self.assertErro(saida)
                self.assertIn(type(erro).__name__, saida["result"])


# ============================================================
# youtube_search
# ============================================================

class TestYoutubeSearch(CasoFerramentas):

    ENTRADAS = [
        {"id": "abc123", "title": "Video Um", "uploader": "Canal X", "duration": 212},
        {"id": "def456", "title": "Video Dois", "channel": "Canal Y", "duration": None},
    ]

    def test_query_vazia_devolve_erro_sem_usar_yt_dlp(self):
        with YtDlpFalso() as falso:
            saida = st.youtube_search("", 5)
        self.assertErro(saida, "query")
        self.assertEqual(falso.chamadas, [])

    def test_query_none_devolve_erro(self):
        with YtDlpFalso() as falso:
            saida = st.youtube_search(None, 5)
        self.assertErro(saida, "query")
        self.assertEqual(falso.chamadas, [])

    def test_sucesso_monta_ytsearch_e_mapeia_campos(self):
        with YtDlpFalso({"entries": self.ENTRADAS}) as falso:
            saida = st.youtube_search("Post Malone", 5)

        self.assertOkLista(saida, 2)
        self.assertEqual(falso.targets, ["ytsearch5:Post Malone"])
        chamada = falso.chamadas[0]
        self.assertFalse(chamada["download"])
        self.assertTrue(chamada["opts"]["quiet"])
        self.assertTrue(chamada["opts"]["no_warnings"])
        self.assertTrue(chamada["opts"]["extract_flat"])
        self.assertTrue(chamada["opts"]["skip_download"])
        self.assertEqual(saida["results"][0], {
            "titulo": "Video Um",
            "url": "https://www.youtube.com/watch?v=abc123",
            "id": "abc123",
            "canal": "Canal X",
            "duracao": 212,
        })
        self.assertEqual(saida["results"][1]["canal"], "Canal Y")
        self.assertIsNone(saida["results"][1]["duracao"])

    def test_entrada_sem_id_usa_url_da_entrada(self):
        entradas = [{"title": "Sem id", "url": "https://youtube.com/playlist?v=1", "uploader": "C"}]
        with YtDlpFalso({"entries": entradas}):
            saida = st.youtube_search("q", 5)
        self.assertEqual(saida["results"][0]["url"], "https://youtube.com/playlist?v=1")
        self.assertEqual(saida["results"][0]["id"], "")

    def test_entrada_sem_canal_fica_com_string_vazia(self):
        with YtDlpFalso({"entries": [{"id": "1", "title": "T"}]}):
            saida = st.youtube_search("q", 5)
        self.assertEqual(saida["results"][0]["canal"], "")

    def test_entradas_none_sao_ignoradas(self):
        with YtDlpFalso({"entries": [None, {"id": "1", "title": "T"}, None]}):
            saida = st.youtube_search("q", 5)
        self.assertOkLista(saida, 1)

    def test_entradas_vazias_devolvem_erro(self):
        with YtDlpFalso({"entries": []}):
            self.assertErro(st.youtube_search("q", 5), "Nenhum video encontrado")

    def test_info_sem_entries_devolve_erro(self):
        with YtDlpFalso({"title": "sem entries"}):
            self.assertErro(st.youtube_search("q", 5), "Nenhum video encontrado")

    def test_info_none_devolve_erro_estruturado(self):
        with YtDlpFalso(None):
            self.assertErro(st.youtube_search("q", 5), "AttributeError")

    def test_info_nao_dict_devolve_erro_estruturado(self):
        with YtDlpFalso(["lista", "inesperada"]):
            self.assertErro(st.youtube_search("q", 5), "AttributeError")

    def test_erro_do_yt_dlp_devolve_erro_estruturado(self):
        with YtDlpFalso(RuntimeError("DownloadError: 403")):
            self.assertErro(st.youtube_search("q", 5), "RuntimeError")

    def test_construtor_do_yt_dlp_a_falhar_devolve_erro(self):
        with mock.patch.dict(sys.modules, {"yt_dlp": modulo_yt_dlp_que_explode(ImportError("boom"))}):
            self.assertErro(st.youtube_search("q", 5), "ImportError")

    def test_yt_dlp_ausente_devolve_erro_estruturado(self):
        with mock.patch.dict(sys.modules, {"yt_dlp": None}):
            self.assertErro(st.youtube_search("q", 5), "ModuleNotFoundError")

    def test_max_resultados_entra_no_prefixo_ytsearch(self):
        for limite, esperado in ((0, "ytsearch0:Termo"), (1, "ytsearch1:Termo"), (10000, "ytsearch10000:Termo")):
            with self.subTest(limite=limite):
                with YtDlpFalso({"entries": self.ENTRADAS}) as falso:
                    st.youtube_search("Termo", limite)
                self.assertEqual(falso.targets, [esperado])

    def test_max_resultados_negativo_gera_alvo_invalido(self):
        # Documenta: nenhuma validacao de limites -> "ytsearch-1:..." e enviado
        # ao provider (que, com o dublê, devolve tudo).
        with YtDlpFalso({"entries": self.ENTRADAS}) as falso:
            saida = st.youtube_search("Termo", -1)
        self.assertEqual(falso.targets, ["ytsearch-1:Termo"])
        self.assertEqual(saida["status"], "ok")

    @unittest.expectedFailure
    def test_bug_max_resultados_nao_e_aplicado_na_lista(self):
        # BUG: youtube_search delega o limite ao provider e nunca corta a lista
        # (linhas 140-152), ao contrario de youtube_channel_latest (linha 236).
        # Com o provider a devolver 5 entradas e max_resultados=2, devolve 5.
        entradas = [{"id": f"v{i}", "title": f"T{i}"} for i in range(5)]
        with YtDlpFalso({"entries": entradas}):
            saida = st.youtube_search("q", 2)
        self.assertLessEqual(len(saida["results"]), 2)

    def test_1000_entradas_sao_serializadas(self):
        entradas = [{"id": f"v{i}", "title": f"T{i}", "uploader": "C"} for i in range(1000)]
        with YtDlpFalso({"entries": entradas}):
            saida = st.youtube_search("q", 1000)
        self.assertOkLista(saida, 1000)
        self.assertEqual(saida["results"][-1]["id"], "v999")

    def test_unicode_e_emoji_preservados_no_json(self):
        entradas = [{"id": "1", "title": "Caf\u00e9 \U0001f600", "uploader": "Canal \u00e7\u00e3o"}]
        with YtDlpFalso({"entries": entradas}):
            saida = st.youtube_search("q", 5)
        self.assertIn("\U0001f600", saida["result"])
        self.assertEqual(json.loads(saida["result"])["results"][0]["titulo"], "Caf\u00e9 \U0001f600")

    def test_titulo_com_aspas_nao_quebra_o_json(self):
        entradas = [{"id": "1", "title": 'x","evil":"1', "uploader": "\n\t"}]
        with YtDlpFalso({"entries": entradas}):
            saida = st.youtube_search("q", 5)
        corpo = json.loads(saida["result"])
        self.assertEqual(corpo["results"][0]["titulo"], 'x","evil":"1')
        self.assertNotIn("evil", corpo)


# ============================================================
# youtube_channel_latest
# ============================================================

class TestYoutubeChannelLatest(CasoFerramentas):

    INFO = {
        "uploader": "Post Malone",
        "entries": [
            {"id": "v1", "title": "Um", "duration": 100},
            {"id": "v2", "title": "Dois", "duration": None},
        ],
    }

    def test_channel_vazio_ou_none_devolve_erro_sem_usar_yt_dlp(self):
        for canal in ("", None):
            with self.subTest(canal=canal):
                with YtDlpFalso() as falso:
                    saida = st.youtube_channel_latest(canal, 3)
                self.assertErro(saida, "channel")
                self.assertEqual(falso.chamadas, [])

    def test_channel_so_com_espacos_nao_e_rejeitado(self):
        # Documenta: o teste `if not channel` acontece ANTES do strip(), logo
        # "   " passa a validacao e acaba no erro generico das duas tentativas.
        with YtDlpFalso() as falso:
            saida = st.youtube_channel_latest("   ", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")
        self.assertEqual(falso.targets, [
            "https://www.youtube.com/@/videos",  # handle esvaziado pelo lstrip
            "ytsearch5:   ",                     # fallback busca o canal original
        ])

    def test_handle_e_normalizado_para_minusculas_sem_arroba(self):
        with YtDlpFalso(self.INFO) as falso:
            saida = st.youtube_channel_latest("@MrBeast", 3)
        self.assertEqual(falso.targets, ["https://www.youtube.com/@mrbeast/videos"])
        self.assertEqual(falso.chamadas[0]["opts"]["playlistend"], 3)
        self.assertTrue(falso.chamadas[0]["opts"]["extract_flat"])
        self.assertFalse(falso.chamadas[0]["download"])
        self.assertEqual(saida["status"], "ok")

    def test_nome_com_espacos_e_arroba_extra(self):
        with YtDlpFalso(self.INFO) as falso:
            st.youtube_channel_latest("  @@Post Malone  ", 5)
        self.assertEqual(falso.targets, ["https://www.youtube.com/@postmalone/videos"])

    def test_url_http_e_usada_tal_e_qual(self):
        alvo = "http://www.youtube.com/@x/videos"
        with YtDlpFalso(self.INFO) as falso:
            st.youtube_channel_latest(alvo, 2)
        self.assertEqual(falso.targets, [alvo])

    def test_sucesso_mapeia_campos_e_canal(self):
        with YtDlpFalso(self.INFO):
            saida = st.youtube_channel_latest("@postmalone", 3)
        self.assertOkLista(saida, 2)
        self.assertEqual(saida["results"][0], {
            "titulo": "Um",
            "url": "https://www.youtube.com/watch?v=v1",
            "id": "v1",
            "canal": "Post Malone",
            "duracao": 100,
        })
        self.assertIsNone(saida["results"][1]["duracao"])

    def test_canal_usa_title_quando_nao_ha_uploader(self):
        info = {"title": "Nome do canal", "entries": [{"id": "v1", "title": "T"}]}
        with YtDlpFalso(info):
            saida = st.youtube_channel_latest("@x", 3)
        self.assertEqual(saida["results"][0]["canal"], "Nome do canal")

    def test_canal_fica_vazio_quando_nada_e_devolvido(self):
        info = {"entries": [{"id": "v1", "title": "T"}]}
        with YtDlpFalso(info):
            saida = st.youtube_channel_latest("@x", 3)
        self.assertEqual(saida["results"][0]["canal"], "")

    def test_entradas_limitadas_por_max_resultados(self):
        info = {"uploader": "C", "entries": [{"id": f"v{i}", "title": f"T{i}"} for i in range(5)]}
        with YtDlpFalso(info):
            saida = st.youtube_channel_latest("@c", 2)
        self.assertOkLista(saida, 2)

    def test_max_resultados_zero_devolve_erro(self):
        with YtDlpFalso(self.INFO):
            self.assertErro(st.youtube_channel_latest("@c", 0), "sem videos acessiveis")

    def test_max_resultados_10000_vai_para_playlistend(self):
        with YtDlpFalso(self.INFO) as falso:
            st.youtube_channel_latest("@c", 10000)
        self.assertEqual(falso.chamadas[0]["opts"]["playlistend"], 10000)

    def test_info_vazio_devolve_erro(self):
        with YtDlpFalso({}):
            self.assertErro(st.youtube_channel_latest("@c", 3), "retornou vazio")

    def test_info_none_devolve_erro_estruturado(self):
        with YtDlpFalso(None):
            self.assertErro(st.youtube_channel_latest("@c", 3), "retornou vazio")

    def test_entries_vazias_devolvem_erro(self):
        with YtDlpFalso({"uploader": "C", "entries": []}):
            self.assertErro(st.youtube_channel_latest("@c", 3), "sem videos acessiveis")

    def test_entries_so_com_none_devolvem_erro(self):
        with YtDlpFalso({"uploader": "C", "entries": [None, None]}):
            self.assertErro(st.youtube_channel_latest("@c", 3), "sem videos acessiveis")

    def test_entradas_none_sao_ignoradas(self):
        info = {"uploader": "C", "entries": [None, {"id": "v1", "title": "T"}]}
        with YtDlpFalso(info):
            self.assertOkLista(st.youtube_channel_latest("@c", 3), 1)

    def test_fallback_por_nome_encontra_uploader_url(self):
        info_busca = {"entries": [
            {"uploader": "Outro Canal", "uploader_url": "https://www.youtube.com/@outro"},
            {"uploader": "Post Malone", "uploader_url": "https://www.youtube.com/@postmalone"},
        ]}
        with YtDlpFalso(RuntimeError("handle direto falhou"), info_busca, self.INFO) as falso:
            saida = st.youtube_channel_latest("Post Malone", 3)

        self.assertEqual(saida["status"], "ok")
        self.assertEqual(falso.targets, [
            "https://www.youtube.com/@postmalone/videos",
            "ytsearch5:Post Malone",
            "https://www.youtube.com/@postmalone",
        ])
        self.assertEqual(falso.chamadas[1]["opts"]["playlistend"], 3)
        self.assertEqual(saida["results"][0]["canal"], "Post Malone")

    def test_fallback_sem_correspondencia_devolve_erro_com_dica(self):
        info_busca = {"entries": [{"uploader": "Nada a ver", "uploader_url": "https://x"}]}
        with YtDlpFalso(RuntimeError("403"), info_busca) as falso:
            saida = st.youtube_channel_latest("Post Malone", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")
        self.assertIn("handle direto (RuntimeError)", saida["result"])
        self.assertIn("busca por nome (RuntimeError)", saida["result"])
        self.assertEqual(len(falso.chamadas), 2)

    def test_fallback_quando_a_busca_tambem_falha(self):
        with YtDlpFalso(RuntimeError("primeira"), ValueError("segunda")) as falso:
            saida = st.youtube_channel_latest("Post Malone", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")
        self.assertIn("handle direto (RuntimeError)", saida["result"])
        self.assertIn("busca por nome (ValueError)", saida["result"])
        self.assertEqual(len(falso.chamadas), 2)

    def test_fallback_quando_a_extracao_do_canal_encontrado_falha(self):
        info_busca = {"entries": [{"uploader": "Post Malone", "uploader_url": "https://www.youtube.com/@pm"}]}
        with YtDlpFalso(RuntimeError("primeira"), info_busca, RuntimeError("terceira")):
            saida = st.youtube_channel_latest("Post Malone", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")

    def test_fallback_com_uploader_url_vazia_devolve_erro(self):
        info_busca = {"entries": [{"uploader": "Post Malone", "uploader_url": ""}]}
        with YtDlpFalso(RuntimeError("primeira"), info_busca):
            saida = st.youtube_channel_latest("Post Malone", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")

    def test_palavras_curtas_nao_geram_correspondencia(self):
        # "de" tem 2 letras -> filtrada por len(p) > 2; sem correspondencia.
        info_busca = {"entries": [{"uploader": "de", "uploader_url": "https://www.youtube.com/@de"}]}
        with YtDlpFalso(RuntimeError("primeira"), info_busca):
            saida = st.youtube_channel_latest("de", 3)
        self.assertErro(saida, "Nao consegui acessar o canal")

    def test_yt_dlp_ausente_devolve_erro_estruturado(self):
        with mock.patch.dict(sys.modules, {"yt_dlp": None}):
            self.assertErro(st.youtube_channel_latest("@c", 3), "ModuleNotFoundError")

    def test_canal_com_emoji_e_caracteres_hostis_nao_levanta(self):
        for canal in ("@canal\U0001f600", "@a\r\nb", "@canal com 'aspas' e \"duplas\"", "@" * 5, "@"):
            with self.subTest(canal=repr(canal)):
                with YtDlpFalso(self.INFO) as falso:
                    saida = st.youtube_channel_latest(canal, 3)
                self.assertIsInstance(saida, dict)
                self.assertEqual(len(falso.chamadas), 1)

    def test_arroba_repetido_gera_alvo_degenerado(self):
        # Documenta: lstrip("@") esvazia o handle e nenhuma validacao impede o
        # alvo "https://www.youtube.com/@/videos".
        with YtDlpFalso(self.INFO) as falso:
            saida = st.youtube_channel_latest("@@", 3)
        self.assertEqual(falso.targets, ["https://www.youtube.com/@/videos"])
        self.assertEqual(saida["status"], "ok")

    @unittest.expectedFailure
    def test_bug_max_resultados_negativo_devolve_todos_menos_um(self):
        # BUG: linha 236 faz info["entries"][:max_resultados]; com um limite
        # negativo o slice Python devolve len-1 itens (2 de 3) em vez de 0/erro.
        # youtube_search rejeita/normaliza de forma diferente (gera ytsearch-1:).
        info = {"uploader": "C", "entries": [{"id": f"v{i}", "title": f"T{i}"} for i in range(3)]}
        with YtDlpFalso(info):
            saida = st.youtube_channel_latest("@c", -1)
        self.assertErro(saida)


# ============================================================
# get_current_url / read_page_structured (via _post)
# ============================================================

class TestRotasDoNavegador(CasoFerramentas):

    PAYLOAD_PAGINA = {
        "status": "ok",
        "url": "https://exemplo.com/pagina",
        "texto": "ola mundo",
        "links": [{"texto": "Ir", "href": "/ir"}],
        "botoes": [{"texto": "Enviar"}],
        "inputs": [{"tipo": "text", "name": "q", "placeholder": ""}],
        "total_links": 1,
        "total_botoes": 1,
    }

    # -- get_current_url ------------------------------------------------
    def test_get_current_url_chama_a_rota_com_timeout_10(self):
        with self.patch_interno(return_value={"status": "ok", "url": "https://x"}) as falso:
            saida = st.get_current_url()
        falso.assert_called_once_with("/get_current_url", {}, timeout=10)
        self.assertEqual(saida, {"status": "ok", "result": "https://x", "url": "https://x"})

    def test_get_current_url_sem_url_devolve_string_vazia(self):
        with self.patch_interno(return_value={"status": "ok"}):
            saida = st.get_current_url()
        self.assertEqual(saida["status"], "ok")
        self.assertEqual(saida["url"], "")
        self.assertEqual(saida["result"], "")

    def test_get_current_url_propaga_erro_do_backend_sem_alterar(self):
        erro = {"status": "erro", "result": "playwright nao iniciado"}
        with self.patch_interno(return_value=erro):
            self.assertEqual(st.get_current_url(), erro)

    def test_get_current_url_backend_nao_dict_devolve_erro(self):
        for payload in (["lista"], "texto", 42, None):
            with self.subTest(payload=payload):
                with self.patch_interno(return_value=payload):
                    saida = st.get_current_url()
                self.assertIsInstance(saida, dict)
                self.assertErro(saida)

    def test_get_current_url_excepcao_no_post_devolve_erro(self):
        with self.patch_interno(side_effect=requests.exceptions.Timeout("t")):
            self.assertErro(st.get_current_url(), "Timeout")

    def test_get_current_url_preserva_url_unicode(self):
        with self.patch_interno(return_value={"status": "ok", "url": "https://a.com/caf\u00e9?\U0001f600"}):
            saida = st.get_current_url()
        self.assertEqual(saida["url"], "https://a.com/caf\u00e9?\U0001f600")
        self.assertEqual(saida["result"], saida["url"])

    # -- read_page_structured -------------------------------------------
    def test_read_page_chama_a_rota_com_timeout_15(self):
        with self.patch_interno(return_value=self.PAYLOAD_PAGINA) as falso:
            st.read_page_structured()
        falso.assert_called_once_with("/read_page_structured", {}, timeout=15)

    def test_read_page_sucesso_json_valido_e_campos_propagados(self):
        with self.patch_interno(return_value=dict(self.PAYLOAD_PAGINA)):
            saida = st.read_page_structured()

        self.assertEqual(saida["status"], "ok")
        self.assertIsInstance(saida["result"], str)
        self.assertEqual(json.loads(saida["result"]), self.PAYLOAD_PAGINA)
        self.assertEqual(saida["url"], self.PAYLOAD_PAGINA["url"])
        self.assertEqual(saida["texto"], "ola mundo")
        self.assertEqual(saida["links"], self.PAYLOAD_PAGINA["links"])
        self.assertEqual(saida["total_links"], 1)
        self.assertEqual(saida["total_botoes"], 1)

    def test_read_page_propaga_erro_do_backend_sem_alterar(self):
        erro = {"status": "erro", "result": "RuntimeError: browser fechado"}
        with self.patch_interno(return_value=erro):
            self.assertEqual(st.read_page_structured(), erro)

    def test_read_page_backend_nao_dict_devolve_erro(self):
        for payload in (["lista"], "texto", 42, None):
            with self.subTest(payload=payload):
                with self.patch_interno(return_value=payload):
                    self.assertErro(st.read_page_structured())

    def test_read_page_excepcao_no_post_devolve_erro(self):
        with self.patch_interno(side_effect=requests.exceptions.ConnectionError("c")):
            self.assertErro(st.read_page_structured(), "ConnectionError")

    def test_read_page_preserva_unicode_sem_escapes_ascii(self):
        payload = {"status": "ok", "texto": "caf\u00e9 \U0001f600", "url": "https://a.com"}
        with self.patch_interno(return_value=payload):
            saida = st.read_page_structured()
        self.assertIn("caf\u00e9 \U0001f600", saida["result"])
        self.assertNotIn("\\u00e9", saida["result"])
        self.assertEqual(json.loads(saida["result"]), payload)

    def test_read_page_status_do_backend_sobrepoe_se_ao_ok_interno(self):
        # Documenta o efeito do spread ``**result`` (linha 286): o "status" do
        # backend sobrescreve o "ok" literal, logo a ferramenta pode devolver um
        # status que nao e nem "ok" nem "erro" (ex.: "pendente"/None).
        with self.patch_interno(return_value={}):
            self.assertEqual(st.read_page_structured()["status"], "ok")
        with self.patch_interno(return_value={"status": "pendente"}):
            self.assertEqual(st.read_page_structured()["status"], "pendente")
        with self.patch_interno(return_value={"status": None}):
            self.assertIsNone(st.read_page_structured()["status"])

    def test_nenhuma_rota_levanta_com_backend_hostil(self):
        hostis = [None, [], {}, "erro", 0, {"status": "erro"}, {"status": "erro", "result": None}]
        for payload in hostis:
            with self.subTest(payload=payload):
                with self.patch_interno(return_value=payload):
                    self.assertIsInstance(st.get_current_url(), dict)
                    self.assertIsInstance(st.read_page_structured(), dict)


# ============================================================
# registrar_todas
# ============================================================

class TestRegistrarTodas(CasoFerramentas):

    ESPERADAS = {
        "search_google_structured",
        "web_search_structured",
        "youtube_search",
        "youtube_channel_latest",
        "get_current_url",
        "read_page_structured",
    }

    def _registrar(self):
        registos: list[tuple[str, object, str]] = []
        st.registrar_todas(lambda nome, fn, desc: registos.append((nome, fn, desc)))
        return registos

    def test_registra_as_seis_ferramentas_com_as_funcoes_reais(self):
        registos = self._registrar()
        self.assertEqual(len(registos), 6)
        nomes = [r[0] for r in registos]
        self.assertEqual(set(nomes), self.ESPERADAS)
        self.assertEqual(len(set(nomes)), 6, "nomes duplicados")
        for nome, funcao, _desc in registos:
            self.assertIs(funcao, getattr(st, nome))
            self.assertTrue(callable(funcao))

    def test_descricoes_sao_unicas_e_uteis(self):
        registos = self._registrar()
        descricoes = [r[2] for r in registos]
        self.assertEqual(len(set(descricoes)), 6)
        for _nome, _fn, desc in registos:
            self.assertIsInstance(desc, str)
            self.assertTrue(desc.strip())
        por_nome = {nome: desc for nome, _fn, desc in registos}
        for nome in ("search_google_structured", "web_search_structured", "youtube_search"):
            self.assertIn("query", por_nome[nome])
        self.assertIn("channel", por_nome["youtube_channel_latest"])
        self.assertIn("Sem argumentos", por_nome["get_current_url"])

    def test_registrar_todas_chama_o_registrador_uma_vez_por_ferramenta(self):
        nomes: list[str] = []

        def registrar(nome, _fn, _desc):
            nomes.append(nome)

        st.registrar_todas(registrar)
        self.assertEqual(len(nomes), 6)
        self.assertEqual(len(set(nomes)), 6)
        self.assertEqual(set(nomes), self.ESPERADAS)

    def test_erro_do_registrador_nao_e_engolido(self):
        def registrar(_nome, _fn, _desc):
            raise RuntimeError("registo falhou")

        with self.assertRaises(RuntimeError):
            st.registrar_todas(registrar)


# ============================================================
# Garantias de isolamento (nenhuma chamada real)
# ============================================================

class TestIsolamentoDeRede(CasoFerramentas):

    def test_sem_rede_bloqueia_conexao_tcp(self):
        with sem_rede():
            with self.assertRaises(OSError):
                socket.create_connection(("127.0.0.1", 11434), timeout=0.2)

    def test_ferramentas_offline_com_mocks_nao_recorrem_a_rede(self):
        html_g = html_google([(LINK_GOOGLE, "T")])
        html_d = html_ddg([("https://a.com", "T", "S")])
        with self.patch_get(return_value=RespostaFalsa(text=html_g)), \
             self.patch_post(return_value=RespostaFalsa(text=html_d)), \
             self.patch_interno(return_value={"status": "ok", "url": "https://x"}), \
             YtDlpFalso(
                 {"entries": [{"id": "v1", "title": "T"}]},
                 {"uploader": "C", "entries": [{"id": "v1", "title": "T"}]},
             ):
            self.assertEqual(st.search_google_structured("q", 5)["status"], "ok")
            self.assertEqual(st.web_search_structured("q", 5)["status"], "ok")
            self.assertEqual(st.get_current_url()["status"], "ok")
            self.assertEqual(st.read_page_structured()["status"], "ok")
            self.assertEqual(st.youtube_search("q", 5)["status"], "ok")
            self.assertEqual(st.youtube_channel_latest("@c", 3)["status"], "ok")

    def test_ferramentas_de_busca_nao_usam_urllib(self):
        html_g = html_google([(LINK_GOOGLE, "T")])
        html_d = html_ddg([("https://a.com", "T", "S")])
        with mock.patch.object(urllib.request, "urlopen",
                               side_effect=AssertionError("urlopen nao deve ser usado")) as falso, \
             self.patch_get(return_value=RespostaFalsa(text=html_g)), \
             self.patch_post(return_value=RespostaFalsa(text=html_d)):
            self.assertEqual(st.search_google_structured("q", 5)["status"], "ok")
            self.assertEqual(st.web_search_structured("q", 5)["status"], "ok")
        falso.assert_not_called()

    def test_oserror_do_transporte_offline_nao_escapa(self):
        # Reproduz o modo de falha do sem_rede() sem provocar DNS real.
        bloqueio = OSError("rede bloqueada nos testes do MYRA (use mocks)")
        with self.patch_get(side_effect=bloqueio):
            saida = st.search_google_structured("q", 5)
        self.assertErro(saida, "OSError")
        self.assertIn("rede bloqueada", saida["result"])
        with self.patch_post(side_effect=bloqueio):
            saida = st.web_search_structured("q", 5)
        self.assertErro(saida, "OSError")

    def test_nenhuma_chamada_escapa_por_requests_api(self):
        # Guarda a cobertura dos mocks: as ferramentas falam DIRETAMENTE com
        # requests.get/post (linhas ~47 e ~86). Se alguem trocar por
        # requests.api.request/Session, estes testes deixariam de mockar a rede
        # real -- aqui isso falha de forma explicita.
        html_g = html_google([(LINK_GOOGLE, "T")])
        html_d = html_ddg([("https://a.com", "T", "S")])
        with mock.patch.object(requests.api, "request",
                               side_effect=AssertionError("chamada nao mockada")) as api_falso, \
             self.patch_get(return_value=RespostaFalsa(text=html_g)), \
             self.patch_post(return_value=RespostaFalsa(text=html_d)):
            self.assertEqual(st.search_google_structured("q", 5)["status"], "ok")
            self.assertEqual(st.web_search_structured("q", 5)["status"], "ok")
        api_falso.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
