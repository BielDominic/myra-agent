# -*- coding: utf-8 -*-
"""Testes severos de ``tasks/system_tools.py`` (27 wrappers + helper ``_post``).

Estrategia
----------
* Cada wrapper e exercitado com ``mock.patch.object(system_tools, "_post")`` para
  provar a **rota** e o **payload exacto** (defaults, opcionais, limites).
* O ``_post`` e testado a serio com ``helpers.HTTPFalso`` / ``RespostaHTTPFalsa``:
  JSON valido, JSON invalido, corpo vazio, bytes nao-UTF8, BOM, HTTPError 404/500,
  URLError, ``socket.timeout``, resposta sem ``read()``, payload nao serializavel
  e ``timeout=120``. Em todos os casos tem de sair ``{"status": "erro", ...}``
  sem levantar excecao.
* Integracao wrapper -> ``_post`` (real) -> ``urlopen`` falso, sem rede.
* ``helpers.sem_rede()`` esta activo em todas as chamadas que poderiam abrir
  sockets: nenhum servico real (Ollama, backend :8000, Gmail/SMTP/IMAP, PC,
  Chrome, Internet) e contactado.

Nenhum ficheiro de producao e modificado.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import json
import math
import socket
import sys
import types
import unittest
import urllib.error
import urllib.request
from unittest import mock

import tasks.system_tools as st
from tests.helpers import (
    CasoBase,
    HTTPFalso,
    RespostaHTTPFalsa,
    sem_rede,
)


# ============================================================
# Tabela completa: nome do wrapper -> (rota, args, kwargs)
# ============================================================

TABELA = (
    ("write_file", "/write_file", ("a.txt", "x"), {}),
    ("read_file", "/read_file", ("a.txt",), {}),
    ("list_dir", "/list_dir", (), {}),
    ("delete_file", "/delete_file", ("a.txt",), {}),
    ("create_dir", "/create_dir", ("nova",), {}),
    ("move_file", "/move_file", ("a.txt", "b.txt"), {}),
    ("search_in_files", "/search_in_files", ("termo",), {}),
    ("code_run", "/code_run", ("print(1)",), {}),
    ("run_python", "/run_python", ("print(1)",), {}),
    ("email_list", "/email_list", (), {}),
    ("email_read", "/email_read", (), {}),
    ("email_send", "/email_send", ("a@b.c", "assunto", "corpo"), {}),
    ("email_search", "/email_search", ("termo",), {}),
    ("email_reply", "/email_reply", (), {}),
    ("pc_move_mouse", "/pc_move_mouse", (10, 20), {}),
    ("pc_click", "/pc_click", (), {}),
    ("pc_type_text", "/pc_type_text", ("texto",), {}),
    ("pc_press_key", "/pc_press_key", ("enter",), {}),
    ("pc_hotkey", "/pc_hotkey", (["ctrl", "c"],), {}),
    ("pc_screenshot", "/pc_screenshot", (), {}),
    ("pc_get_windows", "/pc_get_windows", (), {}),
    ("pc_get_active_window", "/pc_get_active_window", (), {}),
    ("pc_focus_window", "/pc_focus_window", ("Titulo",), {}),
    ("get_current_time", "/get_current_time", (), {}),
    ("get_weather", "/get_weather", (), {}),
    ("save_note", "/save_note", ("nota",), {}),
    ("read_notes", "/read_notes", (), {}),
)

# Strings hostis: vazias, SQLi/shell injection, path traversal, controlo,
# bidi override, unicode/emoji e uma string muito longa.
PERIGOSOS = (
    "",
    "   ",
    "' OR 1=1 -- DROP TABLE notas;",
    '"; rm -rf / --no-preserve-root #',
    "../../../Windows/System32/config/SAM",
    "..\\..\\..\\Users\\Administrator\\ntuser.dat",
    "\x00\x01\x02\x7f",
    "\u202e\u202dln -s / /tmp/pwn",
    "🎉🚀👨‍👩‍👧‍👦 café ãõç ñ ü 中文 العربية",
    "a" * 100_000,
)


class _RespostaQuebrada:
    """Resposta cujo ``read()`` rebenta a meio (conexao reiniciada)."""

    def read(self):
        raise OSError("conexao reiniciada")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _RespostaStr:
    """Resposta que devolve ``str`` em vez de ``bytes`` (servidor maluco)."""

    def read(self):
        return "isto nao e bytes"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(codigo: int, url: str = "http://127.0.0.1:8000/x") -> urllib.error.HTTPError:
    corpo = json.dumps({"detail": f"falha {codigo}"}).encode("utf-8")
    return urllib.error.HTTPError(url, codigo, f"Erro {codigo}", {"Content-Type": "application/json"}, io.BytesIO(corpo))


@contextlib.contextmanager
def _erro_http(codigo: int):
    """HTTPError descartavel.

    No Python 3.14 ``urllib.response.addbase`` herda de
    ``tempfile._TemporaryFileWrapper``, cujo ``__del__`` emite ResourceWarning se
    o objecto nao for fechado explicitamente.
    """
    erro = _http_error(codigo)
    try:
        yield erro
    finally:
        with contextlib.suppress(Exception):
            erro.close()


class _BaseComCaptura(CasoBase):
    """Base com utilitarios de captura de rota/payload."""

    def _captura(self, fn, *args, **kwargs):
        """Chama ``fn`` com ``_post`` mockado. Devolve (resultado, rota, payload)."""
        with mock.patch.object(st, "_post", return_value={"status": "ok", "result": "mock"}) as m, sem_rede():
            resultado = fn(*args, **kwargs)
        self.assertEqual(m.call_count, 1, f"{fn.__name__} devia chamar _post exactamente 1 vez")
        chamada = m.call_args
        self.assertEqual(chamada.kwargs, {}, f"{fn.__name__} nao devia passar kwargs a _post")
        self.assertEqual(len(chamada.args), 2, f"{fn.__name__} devia chamar _post(rota, payload)")
        rota, payload = chamada.args
        return resultado, rota, payload

    def _rota_payload(self, fn, *args, **kwargs):
        _, rota, payload = self._captura(fn, *args, **kwargs)
        return rota, payload


# ============================================================
# 1. _post a serio
# ============================================================

class PostRealTestCase(_BaseComCaptura):
    """Contrato do helper ``_post`` com ``urlopen`` sempre substituido."""

    # -- caminho feliz -------------------------------------------------
    def test_sucesso_devolve_json_do_servidor_intacto(self):
        with HTTPFalso(RespostaHTTPFalsa({"status": "ok", "result": "feito"})) as http, sem_rede():
            r = st._post("/rota", {"a": 1})
        self.assertEqual(r, {"status": "ok", "result": "feito"})
        self.assertEqual(http.ultimo["url"], st.API_URL + "/rota")
        self.assertEqual(http.ultimo["payload"], {"a": 1})
        self.assertEqual(http.ultimo["metodo"], "POST")
        self.assertEqual(http.ultimo["timeout"], 120)

    def test_concatena_api_url_com_a_rota(self):
        self.assertEqual(st.API_URL, "http://127.0.0.1:8000")
        with HTTPFalso() as http, sem_rede():
            st._post("/pc_get_windows", {})
        self.assertEqual(http.ultimo["url"], "http://127.0.0.1:8000/pc_get_windows")

    def test_request_tem_metodo_post_content_type_json_e_corpo_utf8(self):
        capturados = []

        def _urlopen(req, timeout=None, *a, **k):
            capturados.append((req, timeout))
            return RespostaHTTPFalsa({"status": "ok"})

        with mock.patch("urllib.request.urlopen", _urlopen), sem_rede():
            st._post("/x", {"emoji": "🎉", "n": 1})

        self.assertEqual(len(capturados), 1)
        req, timeout = capturados[0]
        self.assertEqual(timeout, 120)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "http://127.0.0.1:8000/x")
        cabecalhos = {chave.lower(): valor for chave, valor in req.headers.items()}
        self.assertEqual(cabecalhos.get("content-type"), "application/json")
        self.assertEqual(json.loads(req.data.decode("utf-8")), {"emoji": "🎉", "n": 1})

    def test_payload_unicode_chega_intacto_ao_servidor(self):
        with HTTPFalso() as http, sem_rede():
            st._post("/x", {"texto": "café 🎉 中文"})
        self.assertEqual(http.ultimo["payload"], {"texto": "café 🎉 中文"})

    def test_payload_de_1mb_e_enviado_sem_truncar(self):
        gordo = "x" * 1_000_000
        with HTTPFalso() as http, sem_rede():
            r = st._post("/x", {"conteudo": gordo})
        self.assertEqual(r.get("status"), "ok")
        self.assertEqual(len(http.ultimo["payload"]["conteudo"]), 1_000_000)

    def test_payload_none_e_serializado_como_null(self):
        with HTTPFalso() as http, sem_rede():
            r = st._post("/x", None)
        self.assertEqual(r.get("status"), "ok")
        self.assertIsNone(http.ultimo["payload"])

    def test_nao_muta_o_payload_recebido(self):
        payload = {"a": 1, "b": [1, 2, 3]}
        copia = json.loads(json.dumps(payload))
        with HTTPFalso(), sem_rede():
            st._post("/x", payload)
        self.assertEqual(payload, copia)

    def test_resposta_json_escalar_e_devolvida_tal_qual(self):
        """O helper nao valida o formato: devolve o que o corpo tiver."""
        with HTTPFalso(RespostaHTTPFalsa("42")), sem_rede():
            self.assertEqual(st._post("/x", {}), 42)
        with HTTPFalso(RespostaHTTPFalsa("[]")), sem_rede():
            self.assertEqual(st._post("/x", {}), [])

    def test_rota_com_caracteres_perigosos_nao_e_sanitizada_localmente(self):
        rota = "/x?../../etc/passwd#\x00"
        with HTTPFalso() as http, sem_rede():
            r = st._post(rota, {})
        self.assertEqual(r.get("status"), "ok")
        self.assertEqual(http.ultimo["url"], st.API_URL + rota)

    # -- corpos invalidos ----------------------------------------------
    def test_json_invalido_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa("isso nao e json {{{")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])
        self.assertIsInstance(r["result"], str)

    def test_json_truncado_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa('{"status": "ok", "result":')), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])

    def test_corpo_vazio_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa(b"")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])

    def test_corpo_so_espacos_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa(b"   \n\t ")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])

    def test_corpo_nao_utf8_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa(b"\xff\xfe\x00\x01\x80")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("UnicodeDecodeError", r["result"])

    def test_corpo_com_bom_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa(b"\xef\xbb\xbf{ }")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])

    def test_status_204_sem_corpo_devolve_erro_estruturado(self):
        with HTTPFalso(RespostaHTTPFalsa(b"", status=204)), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("JSONDecodeError", r["result"])

    def test_resposta_sem_read_devolve_erro_estruturado(self):
        """Objecto devolvido por urlopen sem protocolo de context manager."""
        with HTTPFalso(resposta=object()), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("TypeError", r["result"])

    def test_read_que_rebenta_devolve_erro_estruturado(self):
        with HTTPFalso(resposta=_RespostaQuebrada()), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("OSError", r["result"])
        self.assertIn("conexao reiniciada", r["result"])

    def test_read_que_devolve_str_devolve_erro_estruturado(self):
        with HTTPFalso(resposta=_RespostaStr()), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("AttributeError", r["result"])

    # -- erros HTTP / rede ---------------------------------------------
    def test_http_error_500_devolve_erro_estruturado(self):
        with _erro_http(500) as erro, HTTPFalso(erro=erro), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("HTTPError", r["result"])
        self.assertIn("500", r["result"])

    def test_http_error_404_devolve_erro_estruturado(self):
        with _erro_http(404) as erro, HTTPFalso(erro=erro), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("HTTPError", r["result"])
        self.assertIn("404", r["result"])

    def test_http_error_422_devolve_erro_estruturado(self):
        with _erro_http(422) as erro, HTTPFalso(erro=erro), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("HTTPError", r["result"])
        self.assertIn("422", r["result"])

    def test_urlerror_devolve_erro_estruturado(self):
        with HTTPFalso(erro=urllib.error.URLError("nome nao resolvido")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("URLError", r["result"])

    def test_socket_timeout_devolve_erro_estruturado(self):
        with HTTPFalso(erro=socket.timeout("timed out")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("imeout", r["result"])

    def test_oserror_generico_devolve_erro_estruturado(self):
        with HTTPFalso(erro=OSError("disco cheio")), sem_rede():
            r = st._post("/x", {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("OSError", r["result"])

    def test_nenhuma_excecao_escapa_do_post(self):
        com_corpo = _http_error(500)
        erros = (
            com_corpo,
            urllib.error.URLError("sem dns"),
            socket.timeout("timed out"),
            ConnectionResetError("reset"),
            ValueError("valor invalido"),
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalido"),
            json.JSONDecodeError("esperava valor", "x", 0),
            RuntimeError("rebentou"),
        )
        try:
            for erro in erros:
                with self.subTest(erro=type(erro).__name__):
                    with HTTPFalso(erro=erro), sem_rede():
                        r = st._post("/x", {})
                    self.assertIsInstance(r, dict)
                    self.assertEqual(r["status"], "erro")
                    self.assertIn(type(erro).__name__, r["result"])
        finally:
            with contextlib.suppress(Exception):
                com_corpo.close()

    def test_payload_nao_serializavel_devolve_erro_estruturado(self):
        with HTTPFalso() as http, sem_rede():
            r = st._post("/x", {"obj": object()})
        self.assertEqual(r["status"], "erro")
        self.assertIn("TypeError", r["result"])
        self.assertEqual(http.pedidos, [], "nada devia ter sido enviado")

    def test_rota_none_devolve_erro_estruturado(self):
        with HTTPFalso() as http, sem_rede():
            r = st._post(None, {})
        self.assertEqual(r["status"], "erro")
        self.assertIn("TypeError", r["result"])
        self.assertEqual(http.pedidos, [])

    def test_payload_com_nan_nao_rebenta(self):
        """NaN nao e JSON valido, mas json.dumps aceita-o: documenta o comportamento."""
        with HTTPFalso(RespostaHTTPFalsa({"status": "ok"})) as http, sem_rede():
            r = st._post("/x", {"v": float("nan")})
        self.assertEqual(r["status"], "ok")
        self.assertTrue(math.isnan(http.ultimo["payload"]["v"]))

    # -- sem_rede a serio ----------------------------------------------
    def test_sem_rede_bloqueia_a_ligacao_e_devolve_erro_estruturado(self):
        with sem_rede():
            r = st._post("/get_current_time", {})
        self.assertIsInstance(r, dict)
        self.assertEqual(r["status"], "erro")
        self.assertIn("rede bloqueada", r["result"])

    def test_resultado_de_erro_e_sempre_dict_com_status_erro_e_result_str(self):
        for erro in (ValueError("a"), OSError("b"), socket.timeout("c")):
            with self.subTest(erro=type(erro).__name__):
                with HTTPFalso(erro=erro), sem_rede():
                    r = st._post("/x", {})
                self.assertEqual(set(r.keys()), {"status", "result"})
                self.assertEqual(r["status"], "erro")
                self.assertIsInstance(r["result"], str)
                self.assertTrue(r["result"])


# ============================================================
# 2. Rotas e payloads exactos (com _post mockado)
# ============================================================

class RotasEPayloadsTestCase(_BaseComCaptura):
    """Cada wrapper -> rota e payload exactos."""

    # ----- ARQUIVOS -----
    def test_write_file(self):
        r, rota, payload = self._captura(st.write_file, "notas.txt", "ola")
        self.assertEqual(rota, "/write_file")
        self.assertEqual(payload, {"caminho": "notas.txt", "conteudo": "ola"})
        self.assertEqual(r["status"], "ok")

    def test_read_file(self):
        rota, payload = self._rota_payload(st.read_file, "notas.txt")
        self.assertEqual(rota, "/read_file")
        self.assertEqual(payload, {"caminho": "notas.txt"})

    def test_list_dir_default_e_explicito(self):
        rota, payload = self._rota_payload(st.list_dir)
        self.assertEqual(rota, "/list_dir")
        self.assertEqual(payload, {"caminho": "."})
        rota, payload = self._rota_payload(st.list_dir, "sub/pasta")
        self.assertEqual(rota, "/list_dir")
        self.assertEqual(payload, {"caminho": "sub/pasta"})

    def test_delete_file(self):
        rota, payload = self._rota_payload(st.delete_file, "velho.txt")
        self.assertEqual(rota, "/delete_file")
        self.assertEqual(payload, {"caminho": "velho.txt"})

    def test_create_dir(self):
        rota, payload = self._rota_payload(st.create_dir, "nova/pasta")
        self.assertEqual(rota, "/create_dir")
        self.assertEqual(payload, {"caminho": "nova/pasta"})

    def test_move_file(self):
        rota, payload = self._rota_payload(st.move_file, "a.txt", "b/c.txt")
        self.assertEqual(rota, "/move_file")
        self.assertEqual(payload, {"origem": "a.txt", "destino": "b/c.txt"})
        self.assertEqual(set(payload.keys()), {"origem", "destino"})

    def test_search_in_files_default_e_extensao_explicita(self):
        rota, payload = self._rota_payload(st.search_in_files, "contrato")
        self.assertEqual(rota, "/search_in_files")
        self.assertEqual(payload, {"termo": "contrato", "extensao": ".txt"})
        rota, payload = self._rota_payload(st.search_in_files, "contrato", ".py")
        self.assertEqual(payload, {"termo": "contrato", "extensao": ".py"})

    def test_search_in_files_extensao_vazia_e_passada_tal_qual(self):
        rota, payload = self._rota_payload(st.search_in_files, "x", "")
        self.assertEqual(payload["extensao"], "")

    # ----- CODIGO -----
    def test_code_run_usa_rota_code_run(self):
        rota, payload = self._rota_payload(st.code_run, "print(1)")
        self.assertEqual(rota, "/code_run")
        self.assertEqual(payload, {"codigo": "print(1)"})

    def test_run_python_usa_rota_run_python(self):
        rota, payload = self._rota_payload(st.run_python, "print(1)")
        self.assertEqual(rota, "/run_python")
        self.assertEqual(payload, {"codigo": "print(1)"})

    def test_code_run_e_run_python_nao_sao_equivalentes(self):
        """As duas rotas sao implementacoes diferentes no agent.py."""
        rota_code, payload_code = self._rota_payload(st.code_run, "print(1)")
        rota_run, payload_run = self._rota_payload(st.run_python, "print(1)")
        self.assertNotEqual(rota_code, rota_run)
        self.assertEqual(payload_code, payload_run)
        self.assertIsNot(st.code_run, st.run_python)

    # ----- EMAIL -----
    def test_email_list_default_5_e_sem_pasta_no_payload(self):
        rota, payload = self._rota_payload(st.email_list)
        self.assertEqual(rota, "/email_list")
        self.assertEqual(payload, {"quantidade": 5})
        self.assertNotIn("pasta", payload)

    def test_email_list_limites(self):
        for quantidade in (0, -1, -999, 1, 10000):
            with self.subTest(quantidade=quantidade):
                rota, payload = self._rota_payload(st.email_list, quantidade)
                self.assertEqual(rota, "/email_list")
                self.assertEqual(payload, {"quantidade": quantidade})

    def test_email_list_aceita_tipos_estranhos_sem_validar_localmente(self):
        for valor in (2.5, True, "3", None):
            with self.subTest(valor=valor):
                rota, payload = self._rota_payload(st.email_list, valor)
                self.assertEqual(payload, {"quantidade": valor})

    def test_email_read_default_0(self):
        rota, payload = self._rota_payload(st.email_read)
        self.assertEqual(rota, "/email_read")
        self.assertEqual(payload, {"indice": 0})
        self.assertNotIn("pasta", payload)

    def test_email_read_indice_explicito_e_negativo(self):
        rota, payload = self._rota_payload(st.email_read, 7)
        self.assertEqual(payload, {"indice": 7})
        rota, payload = self._rota_payload(st.email_read, -3)
        self.assertEqual(payload, {"indice": -3})

    def test_email_send(self):
        rota, payload = self._rota_payload(st.email_send, "dest@exemplo.com", "Assunto", "Corpo")
        self.assertEqual(rota, "/email_send")
        self.assertEqual(payload, {"para": "dest@exemplo.com", "assunto": "Assunto", "corpo": "Corpo"})
        self.assertEqual(set(payload.keys()), {"para", "assunto", "corpo"})

    def test_email_search_default_e_explicito_com_pasta_inbox(self):
        rota, payload = self._rota_payload(st.email_search, "fatura")
        self.assertEqual(rota, "/email_search")
        self.assertEqual(payload, {"termo": "fatura", "pasta": "INBOX", "quantidade": 10})
        rota, payload = self._rota_payload(st.email_search, "fatura", 3)
        self.assertEqual(payload, {"termo": "fatura", "pasta": "INBOX", "quantidade": 3})

    def test_email_reply_defaults(self):
        rota, payload = self._rota_payload(st.email_reply)
        self.assertEqual(rota, "/email_reply")
        self.assertEqual(payload, {"indice": 0, "pasta": "INBOX", "corpo": ""})

    def test_email_reply_com_indice_e_corpo(self):
        rota, payload = self._rota_payload(st.email_reply, 4, "obrigado")
        self.assertEqual(payload, {"indice": 4, "pasta": "INBOX", "corpo": "obrigado"})

    # ----- PC -----
    def test_pc_move_mouse_inclui_duration_0_3(self):
        rota, payload = self._rota_payload(st.pc_move_mouse, 100, 200)
        self.assertEqual(rota, "/pc_move_mouse")
        self.assertEqual(payload, {"x": 100, "y": 200, "duration": 0.3})

    def test_pc_move_mouse_com_negativos_e_floats(self):
        rota, payload = self._rota_payload(st.pc_move_mouse, -1920, 0.5)
        self.assertEqual(payload, {"x": -1920, "y": 0.5, "duration": 0.3})

    def test_pc_click_sem_coordenadas_omite_x_e_y(self):
        rota, payload = self._rota_payload(st.pc_click)
        self.assertEqual(rota, "/pc_click")
        self.assertEqual(payload, {"button": "left"})
        self.assertNotIn("x", payload)
        self.assertNotIn("y", payload)

    def test_pc_click_x_none_y_none_explicitos(self):
        rota, payload = self._rota_payload(st.pc_click, None, None)
        self.assertEqual(payload, {"button": "left"})

    def test_pc_click_so_com_x(self):
        rota, payload = self._rota_payload(st.pc_click, 10)
        self.assertEqual(payload, {"button": "left", "x": 10})
        self.assertNotIn("y", payload)

    def test_pc_click_so_com_y(self):
        rota, payload = self._rota_payload(st.pc_click, None, 20)
        self.assertEqual(payload, {"button": "left", "y": 20})
        self.assertNotIn("x", payload)

    def test_pc_click_zero_nao_e_confundido_com_none(self):
        rota, payload = self._rota_payload(st.pc_click, 0, 0)
        self.assertEqual(payload, {"button": "left", "x": 0, "y": 0})

    def test_pc_click_botao_e_coordenadas_completas(self):
        rota, payload = self._rota_payload(st.pc_click, -5, -6, "right")
        self.assertEqual(payload, {"button": "right", "x": -5, "y": -6})

    def test_pc_click_botao_vazio_ou_hostil_passa_tal_qual(self):
        rota, payload = self._rota_payload(st.pc_click, 1, 2, "")
        self.assertEqual(payload["button"], "")
        rota, payload = self._rota_payload(st.pc_click, 1, 2, "left; rm -rf /")
        self.assertEqual(payload["button"], "left; rm -rf /")

    def test_pc_type_text_inclui_interval_0_02(self):
        rota, payload = self._rota_payload(st.pc_type_text, "ola mundo")
        self.assertEqual(rota, "/pc_type_text")
        self.assertEqual(payload, {"text": "ola mundo", "interval": 0.02})

    def test_pc_type_text_vazio_e_unicode(self):
        rota, payload = self._rota_payload(st.pc_type_text, "")
        self.assertEqual(payload, {"text": "", "interval": 0.02})
        rota, payload = self._rota_payload(st.pc_type_text, "🎉 café 中文")
        self.assertEqual(payload["text"], "🎉 café 中文")

    def test_pc_type_text_muito_longo(self):
        texto = "y" * 100_000
        rota, payload = self._rota_payload(st.pc_type_text, texto)
        self.assertEqual(len(payload["text"]), 100_000)
        self.assertEqual(payload["interval"], 0.02)

    def test_pc_press_key(self):
        rota, payload = self._rota_payload(st.pc_press_key, "enter")
        self.assertEqual(rota, "/pc_press_key")
        self.assertEqual(payload, {"key": "enter"})
        rota, payload = self._rota_payload(st.pc_press_key, "")
        self.assertEqual(payload, {"key": ""})

    def test_pc_hotkey_dois_itens(self):
        rota, payload = self._rota_payload(st.pc_hotkey, ["ctrl", "c"])
        self.assertEqual(rota, "/pc_hotkey")
        self.assertEqual(payload, {"keys": ["ctrl", "c"]})

    def test_pc_hotkey_lista_vazia(self):
        rota, payload = self._rota_payload(st.pc_hotkey, [])
        self.assertEqual(payload, {"keys": []})

    def test_pc_hotkey_um_item(self):
        rota, payload = self._rota_payload(st.pc_hotkey, ["esc"])
        self.assertEqual(payload, {"keys": ["esc"]})

    def test_pc_hotkey_50_itens_preserva_ordem(self):
        teclas = [f"k{i}" for i in range(50)]
        rota, payload = self._rota_payload(st.pc_hotkey, teclas)
        self.assertEqual(payload["keys"], teclas)
        self.assertEqual(len(payload["keys"]), 50)

    def test_pc_hotkey_nao_copia_a_lista_do_chamador(self):
        """A lista e enviada por referencia (sem copia defensiva)."""
        teclas = ["ctrl", "v"]
        rota, payload = self._rota_payload(st.pc_hotkey, teclas)
        self.assertEqual(payload["keys"], ["ctrl", "v"])
        self.assertIs(payload["keys"], teclas)
        teclas.append("x")
        self.assertEqual(payload["keys"], ["ctrl", "v", "x"])

    def test_pc_hotkey_com_string_e_tupla_passa_tal_qual(self):
        rota, payload = self._rota_payload(st.pc_hotkey, "ctrl+c")
        self.assertEqual(payload, {"keys": "ctrl+c"})
        rota, payload = self._rota_payload(st.pc_hotkey, ("ctrl", "c"))
        self.assertEqual(payload, {"keys": ("ctrl", "c")})

    def test_pc_screenshot_envia_salvar_true_sem_argumentos(self):
        rota, payload = self._rota_payload(st.pc_screenshot)
        self.assertEqual(rota, "/pc_screenshot")
        self.assertEqual(payload, {"salvar": True})

    def test_pc_get_windows_payload_vazio(self):
        rota, payload = self._rota_payload(st.pc_get_windows)
        self.assertEqual(rota, "/pc_get_windows")
        self.assertEqual(payload, {})

    def test_pc_get_active_window_payload_vazio(self):
        rota, payload = self._rota_payload(st.pc_get_active_window)
        self.assertEqual(rota, "/pc_get_active_window")
        self.assertEqual(payload, {})

    def test_pc_focus_window(self):
        rota, payload = self._rota_payload(st.pc_focus_window, "Bloco de Notas")
        self.assertEqual(rota, "/pc_focus_window")
        self.assertEqual(payload, {"titulo": "Bloco de Notas"})
        rota, payload = self._rota_payload(st.pc_focus_window, "")
        self.assertEqual(payload, {"titulo": ""})

    # ----- UTILITARIAS -----
    def test_get_current_time_sem_argumentos(self):
        rota, payload = self._rota_payload(st.get_current_time)
        self.assertEqual(rota, "/get_current_time")
        self.assertEqual(payload, {})

    def test_get_weather_default_e_cidade_explicita(self):
        rota, payload = self._rota_payload(st.get_weather)
        self.assertEqual(rota, "/get_weather")
        self.assertEqual(payload, {"cidade": ""})
        rota, payload = self._rota_payload(st.get_weather, "São Paulo")
        self.assertEqual(payload, {"cidade": "São Paulo"})

    def test_save_note(self):
        rota, payload = self._rota_payload(st.save_note, "comprar leite")
        self.assertEqual(rota, "/save_note")
        self.assertEqual(payload, {"texto": "comprar leite"})

    def test_read_notes_sem_argumentos(self):
        rota, payload = self._rota_payload(st.read_notes)
        self.assertEqual(rota, "/read_notes")
        self.assertEqual(payload, {})

    def test_tabela_de_rotas_completa_e_sem_duplicados(self):
        rotas_esperadas = [linha[1] for linha in TABELA]
        self.assertEqual(len(rotas_esperadas), 27)
        self.assertEqual(len(set(rotas_esperadas)), 27, "cada rota deve ser unica")
        nomes = [linha[0] for linha in TABELA]
        self.assertEqual(len(set(nomes)), 27)
        for nome, rota, _args, _kwargs in TABELA:
            with self.subTest(nome=nome):
                self.assertTrue(callable(getattr(st, nome)))
                self.assertEqual(rota, "/" + nome)


# ============================================================
# 3. Integracao: wrapper -> _post real -> urlopen falso
# ============================================================

class IntegracaoWrapperTestCase(_BaseComCaptura):
    """Sem mocks do _post: o wrapper tem de produzir o pedido HTTP correcto."""

    def test_todos_os_27_wrappers_geram_pedidos_nas_rotas_certas(self):
        with HTTPFalso(RespostaHTTPFalsa({"status": "ok", "result": "ok"})) as http, sem_rede():
            for nome, _rota, args, kwargs in TABELA:
                with self.subTest(nome=nome):
                    resultado = getattr(st, nome)(*args, **kwargs)
                    self.assertEqual(resultado, {"status": "ok", "result": "ok"})
        self.assertEqual([p["rota"] for p in http.pedidos], [linha[1] for linha in TABELA])
        self.assertEqual(len(http.pedidos), 27)
        self.assertTrue(all(p["metodo"] == "POST" for p in http.pedidos))
        self.assertTrue(all(p["timeout"] == 120 for p in http.pedidos))

    def test_wrapper_sobrevive_a_erro_500_do_servidor(self):
        for nome, _rota, args, kwargs in TABELA:
            with self.subTest(nome=nome):
                with _erro_http(500) as erro, HTTPFalso(erro=erro), sem_rede():
                    r = getattr(st, nome)(*args, **kwargs)
                self.assertEqual(r["status"], "erro")
                self.assertIn("HTTPError", r["result"])

    def test_wrapper_sobrevive_a_json_invalido_do_servidor(self):
        for nome, _rota, args, kwargs in TABELA:
            with self.subTest(nome=nome):
                with HTTPFalso(RespostaHTTPFalsa("<html>gateway timeout</html>")), sem_rede():
                    r = getattr(st, nome)(*args, **kwargs)
                self.assertEqual(r["status"], "erro")
                self.assertIn("JSONDecodeError", r["result"])

    def test_wrapper_repassa_payload_1mb(self):
        gordo = "z" * 1_000_000
        with HTTPFalso() as http, sem_rede():
            r = st.write_file("grande.txt", gordo)
        self.assertEqual(r.get("status"), "ok")
        self.assertEqual(http.ultimo["payload"]["caminho"], "grande.txt")
        self.assertEqual(len(http.ultimo["payload"]["conteudo"]), 1_000_000)

    def test_email_send_com_unicode_e_emoji(self):
        with HTTPFalso() as http, sem_rede():
            st.email_send("a@b.c", "Olá 🎉", "Corpo com acentuação e emoji 🚀")
        self.assertEqual(http.ultimo["payload"]["assunto"], "Olá 🎉")
        self.assertEqual(http.ultimo["payload"]["corpo"], "Corpo com acentuação e emoji 🚀")


# ============================================================
# 4. Contrato severo (argumentos, tipos, limites, strings hostis)
# ============================================================

class ContratoSeveroTestCase(_BaseComCaptura):
    """Faltas de argumentos, excesso, tipos estranhos e strings hostis."""

    CASOS_ARGUMENTO_EM_FALTA = (
        ("write_file_sem_nada", st.write_file, (), {}),
        ("write_file_sem_conteudo", st.write_file, ("a.txt",), {}),
        ("write_file_so_kwarg_conteudo", st.write_file, (), {"conteudo": "x"}),
        ("read_file_sem_caminho", st.read_file, (), {}),
        ("delete_file_sem_caminho", st.delete_file, (), {}),
        ("create_dir_sem_caminho", st.create_dir, (), {}),
        ("move_file_sem_nada", st.move_file, (), {}),
        ("move_file_so_origem", st.move_file, ("a.txt",), {}),
        ("search_in_files_sem_termo", st.search_in_files, (), {}),
        ("code_run_sem_codigo", st.code_run, (), {}),
        ("run_python_sem_codigo", st.run_python, (), {}),
        ("email_send_sem_nada", st.email_send, (), {}),
        ("email_send_sem_corpo", st.email_send, ("a@b.c", "assunto"), {}),
        ("email_search_sem_termo", st.email_search, (), {}),
        ("pc_move_mouse_sem_y", st.pc_move_mouse, (1,), {}),
        ("pc_move_mouse_sem_nada", st.pc_move_mouse, (), {}),
        ("pc_type_text_sem_texto", st.pc_type_text, (), {}),
        ("pc_press_key_sem_key", st.pc_press_key, (), {}),
        ("pc_hotkey_sem_keys", st.pc_hotkey, (), {}),
        ("pc_focus_window_sem_titulo", st.pc_focus_window, (), {}),
        ("save_note_sem_texto", st.save_note, (), {}),
    )

    CASOS_ARGUMENTOS_A_MAIS = (
        ("read_file", st.read_file, ("a.txt", "extra")),
        ("list_dir", st.list_dir, (".", "extra")),
        ("delete_file", st.delete_file, ("a.txt", "extra")),
        ("create_dir", st.create_dir, ("d", "extra")),
        ("search_in_files", st.search_in_files, ("t", ".txt", "extra")),
        ("code_run", st.code_run, ("print(1)", 15)),
        ("run_python", st.run_python, ("print(1)", 15)),
        ("email_list", st.email_list, (5, "INBOX")),
        ("email_read", st.email_read, (0, "INBOX")),
        ("email_send", st.email_send, ("a@b.c", "s", "c", "extra")),
        ("email_search", st.email_search, ("t", 10, "extra")),
        ("email_reply", st.email_reply, (0, "corpo", "extra")),
        ("pc_move_mouse", st.pc_move_mouse, (1, 2, 0.3)),
        ("pc_click", st.pc_click, (1, 2, "left", "extra")),
        ("pc_type_text", st.pc_type_text, ("x", 0.02)),
        ("pc_press_key", st.pc_press_key, ("enter", "extra")),
        ("pc_hotkey", st.pc_hotkey, (["ctrl"], "extra")),
        ("pc_screenshot", st.pc_screenshot, (False,)),
        ("pc_get_windows", st.pc_get_windows, (1,)),
        ("pc_get_active_window", st.pc_get_active_window, (1,)),
        ("pc_focus_window", st.pc_focus_window, ("t", "extra")),
        ("get_current_time", st.get_current_time, (1,)),
        ("get_weather", st.get_weather, ("SP", "extra")),
        ("save_note", st.save_note, ("n", "extra")),
        ("read_notes", st.read_notes, ("extra",)),
    )

    def test_argumentos_obrigatorios_em_falta_levantam_typeerror_sem_chamar_post(self):
        for nome, fn, args, kwargs in self.CASOS_ARGUMENTO_EM_FALTA:
            with self.subTest(caso=nome):
                with mock.patch.object(st, "_post") as m, sem_rede():
                    with self.assertRaises(TypeError):
                        fn(*args, **kwargs)
                self.assertEqual(m.call_count, 0, "nao devia haver pedido HTTP sem argumentos validos")

    def test_argumentos_a_mais_levantam_typeerror_sem_chamar_post(self):
        for nome, fn, args in self.CASOS_ARGUMENTOS_A_MAIS:
            with self.subTest(caso=nome):
                with mock.patch.object(st, "_post") as m, sem_rede():
                    with self.assertRaises(TypeError):
                        fn(*args)
                self.assertEqual(m.call_count, 0)

    def test_wrappers_sem_argumentos_aceitam_chamada_limpa(self):
        for fn in (st.list_dir, st.email_list, st.email_read, st.email_reply, st.pc_click,
                   st.pc_screenshot, st.pc_get_windows, st.pc_get_active_window,
                   st.get_current_time, st.get_weather, st.read_notes):
            with self.subTest(fn=fn.__name__):
                rota, payload = self._rota_payload(fn)
                self.assertTrue(rota.startswith("/"))
                self.assertIsInstance(payload, dict)

    def test_strings_hostis_sao_enviadas_sem_alteracao(self):
        for valor in PERIGOSOS:
            with self.subTest(valor=valor[:20]):
                for fn, campo in ((st.save_note, "texto"), (st.write_file, "caminho"), (st.read_file, "caminho")):
                    with self.subTest(fn=fn.__name__):
                        if fn is st.write_file:
                            rota, payload = self._rota_payload(fn, valor, valor)
                            self.assertEqual(payload["conteudo"], valor)
                        else:
                            rota, payload = self._rota_payload(fn, valor)
                        self.assertEqual(payload[campo], valor)

    def test_strings_hostis_em_email(self):
        for valor in PERIGOSOS:
            with self.subTest(valor=valor[:20]):
                rota, payload = self._rota_payload(st.email_send, "a@b.c", valor, valor)
                self.assertEqual(payload["assunto"], valor)
                self.assertEqual(payload["corpo"], valor)
                rota, payload = self._rota_payload(st.email_search, valor)
                self.assertEqual(payload["termo"], valor)

    def test_strings_hostis_em_pc_e_notas(self):
        for valor in PERIGOSOS:
            with self.subTest(valor=valor[:20]):
                rota, payload = self._rota_payload(st.pc_type_text, valor)
                self.assertEqual(payload["text"], valor)
                rota, payload = self._rota_payload(st.pc_focus_window, valor)
                self.assertEqual(payload["titulo"], valor)
                rota, payload = self._rota_payload(st.pc_press_key, valor)
                self.assertEqual(payload["key"], valor)

    def test_tipos_errados_nunca_rebentam_localmente(self):
        casos = (
            (st.read_file, (123,), {}),
            (st.read_file, (None,), {}),
            (st.write_file, (None, None), {}),
            (st.write_file, (b"bytes", b"bytes"), {}),
            (st.move_file, (123, 456), {}),
            (st.write_file, (["lista"], {"dict": 1}), {}),
            (st.code_run, (123,), {}),
            (st.pc_move_mouse, ("x", "y"), {}),
            (st.pc_type_text, (123,), {}),
            (st.email_send, (1, 2, 3), {}),
            (st.save_note, (object(),), {}),
            (st.pc_hotkey, (None,), {}),
        )
        for fn, args, kwargs in casos:
            with self.subTest(fn=fn.__name__, args=args):
                resultado = self._captura(fn, *args, **kwargs)[0]
                self.assertIsInstance(resultado, dict)

    def test_payloads_vazios_ou_none(self):
        casos = (
            (st.write_file, ("", ""), ("caminho", "conteudo")),
            (st.read_file, ("",), ("caminho",)),
            (st.delete_file, ("",), ("caminho",)),
            (st.create_dir, ("",), ("caminho",)),
            (st.move_file, ("", ""), ("origem", "destino")),
            (st.search_in_files, ("", ""), ("termo", "extensao")),
            (st.code_run, ("",), ("codigo",)),
            (st.run_python, ("",), ("codigo",)),
            (st.email_send, ("", "", ""), ("para", "assunto", "corpo")),
            (st.email_search, ("",), ("termo",)),
            (st.save_note, ("",), ("texto",)),
            (st.pc_press_key, ("",), ("key",)),
        )
        for fn, args, campos in casos:
            with self.subTest(fn=fn.__name__):
                rota, payload = self._rota_payload(fn, *args)
                self.assertTrue(rota.startswith("/"))
                for campo in campos:
                    self.assertEqual(payload[campo], "", f"{campo} devia ir vazio em {payload}")

    def test_assinaturas_publicas_tem_os_defaults_documentados(self):
        esperados = {
            "list_dir": {"caminho": "."},
            "search_in_files": {"extensao": ".txt"},
            "email_list": {"quantidade": 5},
            "email_read": {"indice": 0},
            "email_search": {"quantidade": 10},
            "email_reply": {"indice": 0, "corpo": ""},
            "pc_click": {"x": None, "y": None, "button": "left"},
            "get_weather": {"cidade": ""},
        }
        for nome, defaults in esperados.items():
            with self.subTest(fn=nome):
                assinatura = inspect.signature(getattr(st, nome))
                for parametro, valor in defaults.items():
                    self.assertEqual(assinatura.parameters[parametro].default, valor)

    def test_funcoes_de_pc_sem_efeitos_reais_sao_thin_wrappers(self):
        """pc_* nao pode chamar pyautogui: tudo passa pelo backend HTTP."""
        fonte = inspect.getsource(st)
        for proibido in ("import pyautogui", "import mss", "import smtplib", "import imaplib",
                         "import subprocess", "import requests", "from playwright"):
            self.assertNotIn(proibido, fonte)
        self.assertIn("import urllib.request", fonte)


# ============================================================
# 5. Propagacao de erro
# ============================================================

class PropagacaoErroTestCase(_BaseComCaptura):
    """O erro do backend chega ao chamador sem ser reescrito."""

    def test_wrapper_devolve_o_mesmo_objeto_de_erro(self):
        erro = {"status": "erro", "result": "HTTPError: 500"}
        for nome, _rota, args, kwargs in TABELA:
            with self.subTest(nome=nome):
                with mock.patch.object(st, "_post", return_value=erro) as m, sem_rede():
                    r = getattr(st, nome)(*args, **kwargs)
                self.assertIs(r, erro)
                self.assertEqual(m.call_count, 1)

    def test_wrapper_nao_duplica_nem_envolve_o_erro(self):
        erro = {"status": "erro", "result": "Erro: Timeout"}
        with mock.patch.object(st, "_post", return_value=erro), sem_rede():
            r = st.pc_screenshot()
        self.assertEqual(r, erro)
        self.assertEqual(len(r), 2)

    def test_wrapper_aceita_resposta_sem_status(self):
        with mock.patch.object(st, "_post", return_value={"result": "sem status"}), sem_rede():
            r = st.get_current_time()
        self.assertEqual(r, {"result": "sem status"})

    def test_wrapper_propaga_excecao_se_o_post_estiver_partido(self):
        """Contrato de camada: os wrappers nao adicionam try/except proprio.

        Em producao ``_post`` apanha sempre ``Exception``, portanto esta excecao
        nao e alcancavel pelo planner; o teste fixa o desenho (delegacao fina).
        """
        with mock.patch.object(st, "_post", side_effect=RuntimeError("post partido")), sem_rede():
            with self.assertRaises(RuntimeError):
                st.read_file("a.txt")

    def test_cada_wrapper_chama_post_com_rota_string_e_payload_dict(self):
        for nome, _rota, args, kwargs in TABELA:
            with self.subTest(nome=nome):
                _r, rota, payload = self._captura(getattr(st, nome), *args, **kwargs)
                self.assertIsInstance(rota, str)
                self.assertTrue(rota.startswith("/"))
                self.assertIsInstance(payload, dict)


# ============================================================
# 6. Zero efeitos reais
# ============================================================

def _modulo_falso(nome: str) -> types.ModuleType:
    """Modulo que rebenta em qualquer acesso a atributo."""
    modulo = types.ModuleType(nome)

    def _explode(*args, **kwargs):
        raise AssertionError(f"modulo proibido tocado nos testes: {nome}")

    modulo.__getattr__ = _explode  # PEP 562
    return modulo


class SemEfeitosReaisTestCase(_BaseComCaptura):
    """Nada de PC real, email, subprocessos ou Internet."""

    def test_nenhum_modulo_perigoso_e_tocado_com_post_mockado(self):
        falsos = {
            "pyautogui": _modulo_falso("pyautogui"),
            "mss": _modulo_falso("mss"),
            "requests": _modulo_falso("requests"),
            "playwright": _modulo_falso("playwright"),
            "playwright.sync_api": _modulo_falso("playwright.sync_api"),
        }
        with mock.patch.dict(sys.modules, falsos), \
             mock.patch("subprocess.run", side_effect=AssertionError("subprocess.run proibido")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen proibido")), \
             mock.patch("subprocess.call", side_effect=AssertionError("subprocess.call proibido")), \
             mock.patch("smtplib.SMTP_SSL", side_effect=AssertionError("SMTP proibido")), \
             mock.patch("smtplib.SMTP", side_effect=AssertionError("SMTP proibido")), \
             mock.patch("imaplib.IMAP4_SSL", side_effect=AssertionError("IMAP proibido")), \
             mock.patch("webbrowser.open", side_effect=AssertionError("browser proibido")), \
             mock.patch("os.system", side_effect=AssertionError("os.system proibido")), \
             mock.patch.object(st, "_post", return_value={"status": "ok"}) as m, \
             sem_rede():
            for nome, _rota, args, kwargs in TABELA:
                with self.subTest(nome=nome):
                    self.assertEqual(getattr(st, nome)(*args, **kwargs), {"status": "ok"})
        self.assertEqual(m.call_count, 27)

    def test_todos_os_wrappers_devolvem_erro_estruturado_sem_rede(self):
        with sem_rede():
            for nome, _rota, args, kwargs in TABELA:
                with self.subTest(nome=nome):
                    r = getattr(st, nome)(*args, **kwargs)
                    self.assertIsInstance(r, dict)
                    self.assertEqual(r["status"], "erro")
                    self.assertIn("rede bloqueada", r["result"])

    def test_sem_rede_bloqueia_mesmo_o_socket_directo(self):
        with sem_rede():
            s = socket.socket()
            try:
                with self.assertRaises(OSError):
                    s.connect(("127.0.0.1", 8000))
            finally:
                s.close()

    def test_modulo_nao_importa_o_agent_para_fazer_http(self):
        self.assertFalse(hasattr(st, "app"))
        self.assertEqual(st.API_URL, "http://127.0.0.1:8000")
        self.assertNotIn("1.1.1.1", inspect.getsource(st))


# ============================================================
# 7. Registro no planner
# ============================================================

class RegistroTestCase(_BaseComCaptura):
    """``registrar_todas`` tem de expor as 27 ferramentas."""

    def _coletar(self):
        registros: dict[str, tuple] = {}
        st.registrar_todas(lambda nome, fn, desc: registros.__setitem__(nome, (fn, desc)))
        return registros

    def test_registra_27_ferramentas(self):
        registros = self._coletar()
        self.assertEqual(len(registros), 27)
        self.assertEqual(set(registros), {linha[0] for linha in TABELA})

    def test_mapeia_cada_nome_para_a_funcao_certa(self):
        registros = self._coletar()
        for nome in registros:
            with self.subTest(nome=nome):
                self.assertIs(registros[nome][0], getattr(st, nome))

    def test_descricoes_nao_vazias_e_sem_placeholders(self):
        registros = self._coletar()
        for nome, (_fn, desc) in registros.items():
            with self.subTest(nome=nome):
                self.assertIsInstance(desc, str)
                self.assertGreaterEqual(len(desc.strip()), 10)
                for placeholder in ("TODO", "FIXME", "None", "..."):
                    self.assertNotIn(placeholder, desc)

    def test_nomes_sao_unicos_e_ordenados_por_grupo(self):
        nomes = []
        st.registrar_todas(lambda nome, fn, desc: nomes.append(nome))
        self.assertEqual(len(nomes), 27)
        self.assertEqual(len(set(nomes)), 27)
        self.assertEqual(nomes, [linha[0] for linha in TABELA])

    def test_todos_os_wrappers_publicos_estao_registrados(self):
        registros = self._coletar()
        publicos = {
            nome
            for nome, obj in vars(st).items()
            if not nome.startswith("_")
            and callable(obj)
            and getattr(obj, "__module__", None) == st.__name__
        }
        self.assertEqual(publicos - {"registrar_todas"}, set(registros))

    def test_registrador_invalido_levanta_typeerror(self):
        with self.assertRaises(TypeError):
            st.registrar_todas(None)
        with self.assertRaises(TypeError):
            st.registrar_todas(lambda nome, fn: None)
        with self.assertRaises(TypeError):
            st.registrar_todas()

    def test_registrar_duas_vezes_produz_os_mesmos_27(self):
        primeiro = set(self._coletar())
        segundo = set(self._coletar())
        self.assertEqual(primeiro, segundo)
        self.assertEqual(len(segundo), 27)

    def test_registrador_recebe_sempre_tres_argumentos_do_tipo_certo(self):
        vistos = []

        def _registrar(nome, fn, desc):
            vistos.append((nome, fn, desc))

        st.registrar_todas(_registrar)
        for nome, fn, desc in vistos:
            with self.subTest(nome=nome):
                self.assertIsInstance(nome, str)
                self.assertTrue(callable(fn))
                self.assertIsInstance(desc, str)


# ============================================================
# 8. BUGS de producao (nao corrigidos: apenas documentados)
# ============================================================

class BugsProducaoTestCase(_BaseComCaptura):
    """Testes que falham de proposito: fixam bugs encontrados em producao."""

    @unittest.expectedFailure
    def test_bug_run_python_diz_ser_alias_mas_usa_outra_rota(self):
        """BUG: tasks/system_tools.py:78-80 documenta ``run_python`` como "Alias de
        code_run", mas POSTa /run_python e o agent.py:1874 implementa um
        comportamento diferente (timeout fixo de 15s, sem EXIT CODE, truncagem
        3000/1000 em vez de 5000/2000). Descricao registada no planner
        (linha 216-217) tambem afirma "alias de code_run".
        """
        diz_alias = "alias" in (st.run_python.__doc__ or "").lower()
        rota, _payload = self._rota_payload(st.run_python, "print(1)")
        self.assertTrue(diz_alias and rota == "/code_run",
                        "run_python alega ser alias de code_run mas usa rota propria")

    @unittest.expectedFailure
    def test_bug_email_reply_descricao_diz_corpo_obrigatorio_mas_tem_default(self):
        """BUG: em tasks/system_tools.py:107 ``email_reply`` tem ``corpo: str = ""``,
        mas a descricao registada para o planner (linha 228-229) diz
        "Obrigatorio: corpo. Opcional: indice." — contrato contraditorio: o
        planner pode omitir o corpo e enviar um email de resposta vazio.
        """
        registros = self._coletar_descricoes()
        descricao = registros["email_reply"].lower()
        diz_obrigatorio = "obrigatorio: corpo" in descricao
        tem_default = inspect.signature(st.email_reply).parameters["corpo"].default != inspect.Parameter.empty
        self.assertFalse(diz_obrigatorio and tem_default,
                         "descricao exige corpo mas a assinatura tem default vazio")

    def _coletar_descricoes(self):
        descricoes = {}
        st.registrar_todas(lambda nome, fn, desc: descricoes.__setitem__(nome, desc))
        return descricoes


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
