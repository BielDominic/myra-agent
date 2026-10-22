# -*- coding: utf-8 -*-
"""Testes severos do grupo VISAO/PC do MYRA.

Alvos:
  * ``computer/vision_locate.py`` (funcoes + pipeline fuzzy/LLM)
  * ``computer/controller.py`` (mouse/teclado via pyautogui)
  * ``computer/screen.py`` (screenshot via mss)
  * ``computer/windows.py`` (janelas via pygetwindow/ctypes)
  * rotas ``/vision_locate``, ``/vision_click``, ``/vision_type`` do agent.py

Regras de seguranca aplicadas em TODOS os testes:
  * ``pyautogui``, ``mss``, ``pygetwindow``, ``ctypes.windll.user32``,
    ``rapidocr_onnxruntime`` e ``urllib.request.urlopen`` sao sempre mockados:
    nenhum clique, digitacao, captura de ecra, movimento de janela ou pedido
    HTTP real acontece.
  * ``sem_rede()`` bloqueia socket.connect/create_connection nos testes que
    exercitam o caminho de rede do LLM.
  * ``workspace_temporario()`` (usado nas rotas) e ``AmbienteIsolado`` de
    ``helpers.CasoBase`` mantem o agente isolado num diretorio temporario.

Nenhum ficheiro de producao foi modificado.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

import mss as mss_mod

# Torna ``tests.helpers`` importavel mesmo com execucao direta do ficheiro.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import helpers  # noqa: E402
from tests.helpers import (  # noqa: E402
    HTTPFalso,
    RespostaHTTPFalsa,
    sem_rede,
    workspace_temporario,
)

# ---------------------------------------------------------------------------
# Modulos de producao (o import de computer/controller.py toca em pyautogui a
# nivel de modulo, mas com FAILSAFE/PAUSE atribuidos -- nenhum movimento real).
# ---------------------------------------------------------------------------
from computer import controller as controller_mod  # noqa: E402
from computer import screen as screen_mod  # noqa: E402
from computer import vision_locate as vl  # noqa: E402
from computer import windows as windows_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Fakes reutilizaveis
# ---------------------------------------------------------------------------


class ImgFalsa:
    """Imita o objeto devolvido por ``mss.grab`` (rgb/size/width/height)."""

    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.size = (width, height)
        self.rgb = b"\x00" * 16


class MSSFalso:
    """Substitui o objecto do mss usado pelos modulos (``mss.mss``/``mss.MSS``)."""

    def __init__(self, img: ImgFalsa | None = None, erro: Exception | None = None) -> None:
        self.monitors = [{}, {"left": 0, "top": 0, "width": 640, "height": 480}]
        self._img = img or ImgFalsa()
        self._erro = erro
        self.grabs: list = []

    def grab(self, monitor):
        if self._erro is not None:
            raise self._erro
        self.grabs.append(monitor)
        return self._img

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeRapidOCR:
    """Imita ``rapidocr_onnxruntime.RapidOCR`` devolvendo (resultado, tempo)."""

    def __init__(self, resultado=None) -> None:
        self._resultado = resultado
        self.chamadas: list = []

    def __call__(self, imagem_path):
        self.chamadas.append(imagem_path)
        return self._resultado, 0.01


class PyAutoGUIFalso:
    """pyautogui falso: registra cada chamada, nunca toca no PC.

    Se ``erro`` for definido, TODA chamada levanta essa excecao.
    """

    FAILSAFE = True
    PAUSE = 0.1

    def __init__(self, erro: Exception | None = None) -> None:
        self.erro = erro
        self.chamadas: list[tuple] = []

    def size(self):
        return type("Size", (), {"width": 1920, "height": 1080})()

    def _registrar(self, nome, *args, **kwargs):
        if self.erro is not None:
            raise self.erro
        self.chamadas.append((nome, args, kwargs))

    def __getattr__(self, nome):  # moveTo, click, write, press, hotkey, scroll...
        if nome.startswith("_"):
            raise AttributeError(nome)

        def _fn(*args, **kwargs):
            self._registrar(nome, *args, **kwargs)

        return _fn

    def nomes(self) -> list[str]:
        return [c[0] for c in self.chamadas]

    def chamadas_de(self, nome: str) -> list[tuple]:
        return [c for c in self.chamadas if c[0] == nome]


class PyAutoGUIEstrito:
    """pyautogui falso que valida tipos como o pyautogui real.

    Coordenadas fora do ecra levantam ``FailSafeException`` e valores de tipo
    errado levantam ``TypeError`` -- exatamente o que o pyautogui faz.
    """

    FAILSAFE = True
    PAUSE = 0.1

    def __init__(self, largura: int = 1920, altura: int = 1080) -> None:
        self.largura = largura
        self.altura = altura
        self.chamadas: list[tuple] = []

    def size(self):
        return type("Size", (), {"width": self.largura, "height": self.altura})()

    def _coord(self, x, y):
        for valor in (x, y):
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise TypeError(f"coordenada de tipo invalido: {type(valor).__name__}")
            if valor != valor:  # NaN
                raise TypeError("coordenada NaN")
        if not (0 <= x < self.largura and 0 <= y < self.altura):
            raise RuntimeError(f"FailSafeException: coordenada fora do ecra ({x}, {y})")

    def _registrar(self, nome, *args, **kwargs):
        self.chamadas.append((nome, args, kwargs))

    def moveTo(self, x, y, duration=None):
        self._coord(x, y)
        self._registrar("moveTo", x, y, duration=duration)

    def click(self, *args, **kwargs):
        if args:
            self._coord(args[0], args[1])
        self._registrar("click", *args, **kwargs)

    def write(self, texto, interval=None):
        if not isinstance(texto, str):
            raise TypeError(f"write exige str, veio {type(texto).__name__}")
        self._registrar("write", texto, interval=interval)

    def press(self, tecla):
        if not isinstance(tecla, str) or not tecla:
            raise ValueError(f"tecla invalida: {tecla!r}")
        self._registrar("press", tecla)

    def hotkey(self, *teclas):
        for t in teclas:
            if not isinstance(t, str) or not t:
                raise ValueError(f"tecla invalida: {t!r}")
        self._registrar("hotkey", *teclas)

    def scroll(self, quantidade):
        if isinstance(quantidade, bool) or not isinstance(quantidade, int):
            raise TypeError(f"scroll exige int, veio {type(quantidade).__name__}")
        self._registrar("scroll", quantidade)

    def nomes(self) -> list[str]:
        return [c[0] for c in self.chamadas]

    def chamadas_de(self, nome: str) -> list[tuple]:
        return [c for c in self.chamadas if c[0] == nome]


def janela_falsa(titulo: str = "Bloco de Notas", minimizada: bool = False):
    janela = mock.MagicMock()
    janela.title = titulo
    janela.isMinimized = minimizada
    return janela


class JanelaFalsaGW:
    """pygetwindow falso para windows.py."""

    def __init__(self, titulos=None, ativa=None, erro=None) -> None:
        self._titulos = titulos if titulos is not None else []
        self._ativa = ativa
        self._erro = erro
        self.activates: list = []
        self.restores: list = []

    def getAllWindows(self):
        if self._erro is not None:
            raise self._erro
        return [janela_falsa(t) for t in self._titulos]

    def getActiveWindow(self):
        if self._erro is not None:
            raise self._erro
        return self._ativa

    def getWindowsWithTitle(self, titulo):
        if self._erro is not None:
            raise self._erro
        janelas = [j for j in (janela_falsa(t) for t in self._titulos) if titulo.lower() in j.title.lower()]
        for j in janelas:
            j.activate.side_effect = lambda *_a, **_k: self.activates.append("activate")
            j.restore.side_effect = lambda *_a, **_k: self.restores.append("restore")
        return janelas


def user32_falso(janelas: list[tuple], visivel: bool = True, iconic: bool = False) -> mock.MagicMock:
    """Cria um ``user32`` falso que enumera ``janelas`` (lista de hwnd/titulo)."""
    u = mock.MagicMock()
    u.IsWindowVisible.return_value = visivel
    u.IsIconic.return_value = iconic
    u.EnumWindows.return_value = 1

    def _text_len(hwnd):
        for h, t in janelas:
            if h == hwnd:
                return len(t)
        return 0

    def _text(hwnd, buff, _len):
        for h, t in janelas:
            if h == hwnd:
                buff.value = t
                return len(t)
        return 0

    u.GetWindowTextLengthW.side_effect = _text_len
    u.GetWindowTextW.side_effect = _text
    return u


def enumwindows_executor(u: mock.MagicMock, janelas: list[tuple]) -> None:
    """Faz ``EnumWindows`` invocar o callback para cada janela (como o Windows)."""

    def _enum(callback, lparam):
        for h, _t in janelas:
            if callback(h, lparam) is False:
                break
        return 1

    u.EnumWindows.side_effect = _enum


# ---------------------------------------------------------------------------
# Disponibilidade do agent.py (rotas) -- sem custo quando ja importado
# ---------------------------------------------------------------------------
try:  # pragma: no cover - depende do ambiente
    import agent as agent_mod  # noqa: E402

    AGENT_DISPONIVEL = True
    MOTIVO_AGENT = ""
except Exception as exc:  # pragma: no cover
    agent_mod = None
    AGENT_DISPONIVEL = False
    MOTIVO_AGENT = f"{type(exc).__name__}: {exc}"


# ===========================================================================
# 1. computer/vision_locate.py - funcoes puras (fuzzy/LLM)
# ===========================================================================


class VisionPuroTestCase(helpers.CasoBase):
    """Contrato de _similaridade, _fuzzy_match, _llm_escolher e _ocr."""

    def test_similaridade_identica_e_um(self):
        self.assertEqual(vl._similaridade("New Chat", "New Chat"), 1.0)

    def test_similaridade_ignora_caixa_e_espacos(self):
        self.assertEqual(vl._similaridade("  new chat ", "NEW CHAT"), 1.0)

    def test_similaridade_strings_vazias(self):
        self.assertEqual(vl._similaridade("", ""), 1.0)
        self.assertEqual(vl._similaridade("", "abc"), 0.0)

    def test_similaridade_dentro_do_intervalo(self):
        for a, b in [("abc", "xyz"), ("botao de login", "Sign In"),
                     ("Entrar", "Entrar agora"), ("😀😀", "😀"), ("a" * 5000, "b" * 5000)]:
            valor = vl._similaridade(a, b)
            self.assertGreaterEqual(valor, 0.0)
            self.assertLessEqual(valor, 1.0)

    def test_similaridade_unicode_emoji(self):
        self.assertEqual(vl._similaridade("botao 😀", "botao 😀"), 1.0)
        self.assertAlmostEqual(vl._similaridade("botao", "botao 😀"), 0.8333333, places=5)

    def test_fuzzy_match_lista_vazia(self):
        self.assertEqual(vl._fuzzy_match("login", []), (None, 0.0))

    def test_fuzzy_match_escolhe_o_melhor_e_devolve_similaridade(self):
        elementos = [
            {"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9},
            {"label": "Entrar", "bbox": [0, 20, 10, 30], "conf": 0.9},
        ]
        melhor, sim = vl._fuzzy_match("entrar", elementos)
        self.assertEqual(melhor["label"], "Entrar")
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_fuzzy_match_empate_devolve_um_candidato_valido(self):
        """Empate exato: max() fica com o primeiro, mas nunca com None."""
        elementos = [
            {"label": "Registrar", "bbox": [0, 0, 10, 10], "conf": 0.9},
            {"label": "Entrar agora", "bbox": [0, 20, 10, 30], "conf": 0.9},
        ]
        melhor, sim = vl._fuzzy_match("Entrar", elementos)
        self.assertIn(melhor["label"], ("Registrar", "Entrar agora"))
        self.assertAlmostEqual(sim, 0.6666666, places=5)
        self.assertLess(sim, vl.FUZZY_THRESHOLD)

    def test_fuzzy_match_nao_depende_da_ordem_da_lista(self):
        elementos = [
            {"label": "Sign In", "bbox": [0, 0, 10, 10], "conf": 0.9},
            {"label": "Salvar", "bbox": [0, 20, 10, 30], "conf": 0.9},
        ]
        melhor, _ = vl._fuzzy_match("Sign In", elementos)
        self.assertEqual(melhor["label"], "Sign In")
        melhor2, _ = vl._fuzzy_match("Salvar", list(reversed(elementos)))
        self.assertEqual(melhor2["label"], "Salvar")

    def test_llm_escolher_lista_vazia_nao_chama_rede(self):
        with HTTPFalso() as http:
            self.assertIsNone(vl._llm_escolher("login", []))
        self.assertEqual(http.pedidos, [], "lista vazia nao deve gerar pedido HTTP")

    def test_llm_escolher_resposta_valida_escolhe_candidato(self):
        candidatos = [
            {"label": "Sign In", "bbox": [0, 0, 10, 10], "conf": 0.9},
            {"label": "New Chat", "bbox": [0, 20, 10, 30], "conf": 0.9},
        ]
        corpo = {"message": {"content": "1"}}
        with HTTPFalso(resposta=RespostaHTTPFalsa(corpo)) as http:
            escolhido = vl._llm_escolher("botao de login", candidatos)
        self.assertIsNotNone(escolhido)
        self.assertEqual(escolhido["label"], "New Chat")
        self.assertIn("11434", http.ultimo["url"])
        self.assertEqual(http.ultimo["metodo"], "POST")
        self.assertEqual(http.ultimo["payload"]["stream"], False)
        self.assertIn("Sign In", http.ultimo["payload"]["messages"][0]["content"])

    def test_llm_escolher_texto_lixo_devolve_none(self):
        candidatos = [{"label": "Sign In", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        for conteudo in ["", "nao sei", "desculpe, nao entendi", "null", "###"]:
            with HTTPFalso(resposta=RespostaHTTPFalsa({"message": {"content": conteudo}})):
                self.assertIsNone(vl._llm_escolher("x", candidatos), conteudo)

    def test_llm_escolher_indice_fora_da_lista_devolve_none(self):
        candidatos = [{"label": "Sign In", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        for conteudo in ["7", "99", "0000000042"]:
            with HTTPFalso(resposta=RespostaHTTPFalsa({"message": {"content": conteudo}})):
                self.assertIsNone(vl._llm_escolher("x", candidatos), conteudo)

    def test_llm_escolher_json_invalido_nao_levanta(self):
        candidatos = [{"label": "a", "bbox": [0, 0, 1, 1], "conf": 1.0}]
        for corpo in [b"{isto nao e json", b"", b"[]", b"null", b'{"message": null}',
                      b'{"message": {"content": 42}}']:
            with HTTPFalso(resposta=RespostaHTTPFalsa(corpo)):
                resultado = helpers.sem_excecao(vl._llm_escolher, "x", candidatos)
            self.assertIsNone(resultado, corpo)

    def test_llm_escolher_resposta_sem_message_nao_levanta(self):
        candidatos = [{"label": "a", "bbox": [0, 0, 1, 1], "conf": 1.0}]
        with HTTPFalso(resposta=RespostaHTTPFalsa({"foo": "bar"})):
            self.assertIsNone(vl._llm_escolher("x", candidatos))

    def test_llm_escolher_erro_de_rede_nao_levanta(self):
        candidatos = [{"label": "a", "bbox": [0, 0, 1, 1], "conf": 1.0}]
        with sem_rede():
            # urlopen real tentaria abrir socket -> bloqueado -> None
            self.assertIsNone(vl._llm_escolher("x", candidatos))
        with HTTPFalso(erro=OSError("connection refused")):
            self.assertIsNone(vl._llm_escolher("x", candidatos))
        with HTTPFalso(erro=TimeoutError("timeout")):
            self.assertIsNone(vl._llm_escolher("x", candidatos))
        with HTTPFalso(erro=ValueError("json invalido")):
            self.assertIsNone(vl._llm_escolher("x", candidatos))

    def test_llm_escolher_indexa_sem_estourar_com_lista_grande(self):
        candidatos = [{"label": f"item {i}", "bbox": [0, i, 10, i + 5], "conf": 0.5}
                      for i in range(vl.MAX_CANDIDATOS_LLM)]
        with HTTPFalso(resposta=RespostaHTTPFalsa({"message": {"content": "9"}})):
            escolhido = vl._llm_escolher("item", candidatos)
        self.assertEqual(escolhido["label"], "item 9")

    # -- _ocr ---------------------------------------------------------------

    def _ocr_com(self, resultado):
        ocr = FakeRapidOCR(resultado)
        with mock.patch("rapidocr_onnxruntime.RapidOCR", return_value=ocr):
            elementos = vl._ocr("C:/tmp/nao-existe.png")
        return elementos, ocr

    def test_ocr_resultado_vazio_devolve_lista_vazia(self):
        for resultado in [None, []]:
            elementos, ocr = self._ocr_com(resultado)
            self.assertEqual(elementos, [])
            self.assertEqual(ocr.chamadas, ["C:/tmp/nao-existe.png"])

    def test_ocr_converte_bbox_para_inteiros_e_arredonda_conf(self):
        resultado = [
            ([[10.7, 20.2], [110.9, 20.2], [110.9, 60.8], [10.7, 60.8]], "New Chat", 0.98765),
        ]
        elementos, _ = self._ocr_com(resultado)
        self.assertEqual(len(elementos), 1)
        self.assertEqual(elementos[0]["label"], "New Chat")
        self.assertEqual(elementos[0]["bbox"], [10, 20, 110, 60])
        self.assertEqual(elementos[0]["conf"], 0.988)
        self.assertTrue(all(isinstance(v, int) for v in elementos[0]["bbox"]))

    def test_ocr_filtra_ruido_de_terminal(self):
        resultado = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "[VISION_LOCATE] procurando...", 0.9),
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "PS C:\\computer-agent>", 0.9),
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "status: encontrado: False", 0.9),
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "Enviar", 0.9),
        ]
        elementos, _ = self._ocr_com(resultado)
        self.assertEqual([e["label"] for e in elementos], ["Enviar"])

    def test_ocr_unicode_emoji_e_texto_longo(self):
        resultado = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "🎯 Enviar ✅", 0.9),
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "ç" * 5000, 0.9),
        ]
        elementos, _ = self._ocr_com(resultado)
        self.assertEqual([e["label"] for e in elementos][0], "🎯 Enviar ✅")
        self.assertEqual(len(elementos[1]["label"]), 5000)

    def test_ocr_conf_em_string_e_convertida(self):
        """conf vem do motor de OCR: string numerica nao pode derrubar o pipeline."""
        resultado = [([[0, 0], [10, 0], [10, 10], [0, 10]], "Enviar", "0.9")]
        elementos, _ = self._ocr_com(resultado)
        self.assertEqual(elementos[0]["conf"], 0.9)
        self.assertIsInstance(elementos[0]["conf"], float)

    def test_ocr_erro_do_motor_propaga_para_o_chamador(self):
        with mock.patch("rapidocr_onnxruntime.RapidOCR", side_effect=RuntimeError("modelo ausente")):
            with self.assertRaises(RuntimeError):
                vl._ocr("x.png")


# ===========================================================================
# 2. computer/vision_locate.py - _screenshot e vision_locate
# ===========================================================================


class VisionScreenshotTestCase(helpers.CasoBase):
    """_screenshot usa mss (sempre mockado) e grava no diretorio configurado."""

    def setUp(self):
        super().setUp()
        self.dir_ss = Path(self.tmp) / "screenshots"
        self.dir_ss.mkdir(parents=True, exist_ok=True)

    def _patches(self, mss_fake):
        return [
            mock.patch.object(vl, "SCREENSHOTS_DIR", str(self.dir_ss)),
            # NOTA: ``mss.MSS`` e a classe da API publica enquanto o modulo
            # ``vision_locate`` chama ``mss.MSS()``; sem este patch a captura
            # seria a do ecra REAL.
            mock.patch.object(mss_mod, "MSS", return_value=mss_fake),
        ]

    def test_screenshot_devolve_path_e_dimensoes(self):
        fake = MSSFalso(ImgFalsa(800, 600))
        p1, p2 = self._patches(fake)
        with p1, p2, mock.patch("mss.tools.to_png") as to_png:
            info = vl._screenshot()
        self.assertEqual(info["width"], 800)
        self.assertEqual(info["height"], 600)
        self.assertTrue(info["path"].startswith(str(self.dir_ss)))
        self.assertTrue(os.path.basename(info["path"]).startswith("vision_"))
        self.assertTrue(info["path"].endswith(".png"))
        to_png.assert_called_once()
        self.assertEqual(len(fake.grabs), 1, "deve capturar exatamente um monitor")

    def test_screenshot_dimensoes_zero_nao_quebram(self):
        fake = MSSFalso(ImgFalsa(0, 0))
        p1, p2 = self._patches(fake)
        with p1, p2, mock.patch("mss.tools.to_png"):
            info = vl._screenshot()
        self.assertEqual((info["width"], info["height"]), (0, 0))

    def test_screenshot_erro_do_mss_propaga(self):
        fake = MSSFalso(erro=OSError("sem acesso ao ecra"))
        p1, p2 = self._patches(fake)
        with p1, p2:
            with self.assertRaises(OSError):
                vl._screenshot()


class VisionLocateTestCase(helpers.CasoBase):
    """Contrato completo de ``vision_locate`` (screenshot e OCR sempre mockados)."""

    def setUp(self):
        super().setUp()
        self.dir_ss = Path(self.tmp) / "screenshots"
        self.dir_ss.mkdir(parents=True, exist_ok=True)
        self.ss_path = str(self.dir_ss / "manual.png")
        Path(self.ss_path).write_bytes(b"\x89PNG\r\n\x1a\n")

    # -- helpers ------------------------------------------------------------
    def test_saida_standalone_escapa_unicode_nao_representavel(self):
        class StreamFake:
            def __init__(self):
                self.config = None

            def reconfigure(self, **kwargs):
                self.config = kwargs

        stdout, stderr = StreamFake(), StreamFake()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            vl._configurar_saida_console()
        self.assertEqual(stdout.config, {"errors": "backslashreplace"})
        self.assertEqual(stderr.config, {"errors": "backslashreplace"})

    def _locate(self, descricao, elementos, screenshot_path=None, llm=None):
        """Chama vision_locate com _screenshot/_ocr e (opcional) LLM mockados."""
        patches = [
            mock.patch.object(vl, "SCREENSHOTS_DIR", str(self.dir_ss)),
            mock.patch.object(vl, "_ocr", return_value=elementos),
            mock.patch.object(vl, "_screenshot",
                              return_value={"path": self.ss_path, "width": 640, "height": 480}),
        ]
        if llm is not None:
            patches.append(mock.patch.object(vl, "_llm_escolher", llm))
        for p in patches:
            p.start()
        try:
            return vl.vision_locate(descricao, screenshot_path)
        finally:
            for p in reversed(patches):
                p.stop()

    def _elementos(self):
        return [
            {"label": "New Chat", "bbox": [100, 200, 140, 220], "conf": 0.97},
            {"label": "Configuracoes", "bbox": [10, 10, 30, 30], "conf": 0.88},
        ]

    # -- sucesso ------------------------------------------------------------
    def test_encontrado_por_fuzzy_contrato_completo(self):
        r = self._locate("New Chat", self._elementos())
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["encontrado"])
        self.assertEqual(r["metodo"], "fuzzy")
        self.assertEqual(r["label"], "New Chat")
        self.assertEqual(r["x"], 120)
        self.assertEqual(r["y"], 210)
        self.assertEqual(r["bbox"], [100, 200, 140, 220])
        self.assertEqual(r["conf"], 0.97)
        self.assertEqual(r["screenshot"], self.ss_path)
        self.assertIsInstance(r["result"], str)
        self.assertIn("New Chat", r["result"])

    def test_coordenadas_sao_centro_da_bbox_e_inteiros(self):
        r = self._locate("Config", [{"label": "Config", "bbox": [1, 2, 4, 7], "conf": 1.0}])
        self.assertEqual((r["x"], r["y"]), (2, 4))
        self.assertIsInstance(r["x"], int)
        self.assertIsInstance(r["y"], int)

    def test_bbox_degenerada_origem_zero(self):
        r = self._locate("Ponto", [{"label": "Ponto", "bbox": [0, 0, 0, 0], "conf": 1.0}])
        self.assertEqual((r["x"], r["y"]), (0, 0))
        self.assertTrue(r["encontrado"])

    def test_descricao_unicode_e_emoji_encontra(self):
        r = self._locate("Enviar 🎯", [{"label": "Enviar 🎯", "bbox": [5, 5, 15, 15], "conf": 1.0}])
        self.assertTrue(r["encontrado"])
        self.assertEqual(r["metodo"], "fuzzy")

    def test_descricao_e_espacos_a_direita_encontra(self):
        r = self._locate("   New Chat   ", self._elementos())
        self.assertTrue(r["encontrado"])
        self.assertEqual(r["label"], "New Chat")

    def test_descricao_5000_caracteres_nao_levanta(self):
        elementos = [{"label": "x" * 5000, "bbox": [0, 0, 10, 10], "conf": 1.0}]
        r = self._locate("y" * 5000, elementos, llm=lambda d, c: None)
        self.assertIn(r["status"], ("ok", "erro"))
        self.assertIn("encontrado", r)

    def test_screenshot_path_existente_e_reutilizado(self):
        ss_fake = mock.MagicMock()
        with mock.patch.object(vl, "_ocr", return_value=self._elementos()), \
             mock.patch.object(vl, "_screenshot", ss_fake):
            r = vl.vision_locate("New Chat", self.ss_path)
        ss_fake.assert_not_called()
        self.assertEqual(r["screenshot"], self.ss_path)
        self.assertTrue(r["encontrado"])

    def test_screenshot_path_inexistente_dispara_captura(self):
        with mock.patch.object(vl, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(vl, "_ocr", return_value=self._elementos()), \
             mock.patch.object(vl, "_screenshot",
                               return_value={"path": self.ss_path, "width": 1, "height": 1}) as ss:
            r = vl.vision_locate("New Chat", str(self.dir_ss / "nao_existe.png"))
        ss.assert_called_once()
        self.assertTrue(r["encontrado"])

    def test_screenshot_path_tipos_aceitos_e_ignorados(self):
        for valor in ["", "C:/tmp/nao_existe_xyz.png"]:
            r = self._locate("New Chat", self._elementos(), screenshot_path=valor)
            self.assertEqual(r["status"], "ok")
            self.assertTrue(r["encontrado"])

    def test_screenshot_path_tipo_errado_retorna_erro_estruturado(self):
        for valor in [3.14, [], {}]:
            r = helpers.sem_excecao(vl.vision_locate, "New Chat", valor)
            self.assertTrue(helpers.eh_erro_estruturado(r), repr(valor))
            self.assertIn("screenshot", r["result"].lower())

    # -- caminho ambiguo / LLM ---------------------------------------------
    def test_zona_ambigua_chama_llm_e_usa_resultado(self):
        elementos = [
            {"label": "Entrar agora", "bbox": [0, 40, 20, 60], "conf": 0.9},
            {"label": "Registrar", "bbox": [0, 80, 20, 100], "conf": 0.9},
        ]
        chamadas = []

        def llm(descricao, candidatos):
            chamadas.append((descricao, list(candidatos)))
            return candidatos[0]

        r = self._locate("Entrar", elementos, llm=llm)
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(r["metodo"], "llm")
        self.assertEqual(r["label"], "Entrar agora")
        self.assertEqual((r["x"], r["y"]), (10, 50))

    def test_zona_ambigua_ordena_candidatos_por_y_e_limita_a_10(self):
        # "Ent" (3) vs "Entrar" (6) -> similaridade 0.5 -> zona ambigua (0.3..0.75)
        elementos = [{"label": "Ent" + str(i), "bbox": [0, 1000 - i, 10, 1010 - i], "conf": 0.5}
                     for i in range(25)]
        capturado = {}

        def llm(descricao, candidatos):
            capturado["cands"] = list(candidatos)
            return None

        self._locate("Entrar", elementos, llm=llm)
        cands = capturado["cands"]
        self.assertEqual(len(cands), vl.MAX_CANDIDATOS_LLM)
        ys = [c["bbox"][1] for c in cands]
        self.assertEqual(ys, sorted(ys), "candidatos devem vir ordenados por Y")
        self.assertLess(ys[-1], 990, "os candidatos devem ser os do topo da tela")

    def test_similaridade_baixa_nao_chama_llm(self):
        elementos = [{"label": "zzz", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        llm = mock.MagicMock(return_value=None)
        r = self._locate("login", elementos, llm=llm)
        llm.assert_not_called()
        self.assertFalse(r["encontrado"])
        self.assertEqual(r["metodo"], "none")

    def test_similaridade_exatamente_no_limiar_aceita_sem_llm(self):
        elementos = [{"label": "Entrar", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        llm = mock.MagicMock()
        r = self._locate("Entrar", elementos, llm=llm)
        llm.assert_not_called()
        self.assertTrue(r["encontrado"])
        self.assertEqual(r["metodo"], "fuzzy")
        self.assertGreaterEqual(vl.FUZZY_THRESHOLD, 0.75)

    def test_llm_devolve_none_cai_para_nao_encontrado(self):
        elementos = [{"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        r = self._locate("Entrar", elementos, llm=lambda d, c: None)
        self.assertEqual(r["status"], "erro")
        self.assertFalse(r["encontrado"])
        self.assertEqual(r["metodo"], "none")
        self.assertIn("Entrar", r["result"])

    def test_llm_devolve_elemento_fora_da_lista_usa_bbox_do_llm(self):
        elementos = [{"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        inventado = {"label": "Inventado", "bbox": [50, 50, 60, 60], "conf": 0.1}
        r = self._locate("Entrar", elementos, llm=lambda d, c: inventado)
        self.assertEqual(r["metodo"], "llm")
        self.assertEqual(r["label"], "Inventado")
        self.assertEqual((r["x"], r["y"]), (55, 55))

    def test_llm_nao_pode_gerar_erro_para_o_chamador(self):
        elementos = [{"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9}]

        def llm_quebrado(d, c):
            raise RuntimeError("LLM explodiu")

        with self.assertRaises(RuntimeError):
            # o pipeline NAO protege contra excecao dentro de _llm_escolher
            self._locate("Entrar", elementos, llm=llm_quebrado)

    # -- caminho "alvo nao encontrado" --------------------------------------
    def test_sem_textos_na_tela_devolve_nao_encontrado(self):
        r = self._locate("New Chat", [])
        self.assertEqual(r["status"], "erro")
        self.assertFalse(r["encontrado"])
        self.assertEqual(r["metodo"], "none")
        self.assertIn("Nenhum texto", r["result"])
        self.assertNotIn("x", r, "nao deve devolver coordenadas sem alvo")
        self.assertNotIn("y", r)

    def test_alvo_nao_encontrado_tem_shape_minimo(self):
        r = self._locate("inexistente xyz", [{"label": "abc", "bbox": [0, 0, 1, 1], "conf": 1.0}])
        self.assertFalse(r["encontrado"])
        self.assertIn("screenshot", r)
        self.assertIn("result", r)
        self.assertIn("metodo", r)

    def test_alvo_nao_encontrado_deveria_ser_status_erro(self):
        """O planner precisa receber erro explicito quando o alvo nao existe."""
        r = self._locate("botao que nao existe", [{"label": "abc", "bbox": [0, 0, 1, 1], "conf": 1.0}])
        self.assertEqual(r["status"], "erro", f"alvo nao encontrado deveria ser erro, veio: {r}")

    # -- erros internos nao escapam ----------------------------------------
    def test_erro_no_screenshot_devolve_erro_estruturado(self):
        with mock.patch.object(vl, "_screenshot", side_effect=OSError("sem monitor")), \
             mock.patch.object(vl, "_ocr", return_value=[]):
            r = vl.vision_locate("New Chat")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("sem monitor", r["result"])

    def test_erro_no_ocr_devolve_erro_estruturado(self):
        with mock.patch.object(vl, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(vl, "_screenshot",
                               return_value={"path": self.ss_path, "width": 1, "height": 1}), \
             mock.patch.object(vl, "_ocr", side_effect=RuntimeError("modelo ausente")):
            r = vl.vision_locate("New Chat")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("modelo ausente", r["result"])

    # -- validacao de entrada ----------------------------------------------
    def test_descricao_vazia_ou_so_espacos(self):
        for valor in ["", "   ", "\t", "\n", " \u00a0 "]:
            r = vl.vision_locate(valor)
            self.assertTrue(helpers.eh_erro_estruturado(r), repr(valor))
            self.assertIn("Descricao vazia", r["result"])

    def test_descricao_nao_string_retorna_erro_estruturado(self):
        for valor in [0, 3.14, [], {}, True, 1, None]:
            r = helpers.sem_excecao(vl.vision_locate, valor)
            self.assertTrue(helpers.eh_erro_estruturado(r), f"{valor!r} nao devolveu erro")
            self.assertIn("Descricao", r["result"])

    def test_descricao_vazia_nao_toca_em_screenshot_nem_ocr(self):
        ss = mock.MagicMock()
        ocr = mock.MagicMock()
        with mock.patch.object(vl, "_screenshot", ss), mock.patch.object(vl, "_ocr", ocr):
            r = vl.vision_locate("   ")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        ss.assert_not_called()
        ocr.assert_not_called()

    def test_caracteres_perigosos_na_descricao_nao_quebram(self):
        for valor in ["'; DROP TABLE x; --", "<script>alert(1)</script>", "%s%d{}", "\\x00\\x1b",
                      "a\nb\r\tc", "\u202e reverso", "🔥" * 100]:
            elementos = [{"label": valor, "bbox": [3, 4, 5, 6], "conf": 0.5}]
            r = self._locate(valor, elementos)
            self.assertIsInstance(r, dict)
            self.assertIn(r["status"], ("ok", "erro"))


# ===========================================================================
# 3. computer/vision_locate.py - vision_click e vision_type
# ===========================================================================


class VisionClickTestCase(helpers.CasoBase):
    """``vision_click`` so clica com coordenadas validas e nunca levanta."""

    def _click(self, loc_resultado, pyautogui_falso):
        with mock.patch.object(vl, "vision_locate", return_value=loc_resultado), \
             mock.patch.dict(sys.modules, {"pyautogui": pyautogui_falso}):
            return vl.vision_click("alvo")

    def _loc_ok(self, x=120, y=210, label="New Chat"):
        return {"status": "ok", "encontrado": True, "x": x, "y": y, "label": label,
                "screenshot": "C:/tmp/ss.png", "metodo": "fuzzy", "conf": 0.9}

    def test_clique_bem_sucedido_registra_coordenadas(self):
        fake = PyAutoGUIFalso()
        r = self._click(self._loc_ok(), fake)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["x"], 120)
        self.assertEqual(r["y"], 210)
        self.assertEqual(fake.chamadas_de("click")[0][1], (120, 210))

    def test_overlay_notificado_antes_do_clique(self):
        ordem = []
        fake = PyAutoGUIFalso()
        fake.click = lambda x, y: ordem.append("click")
        callback = lambda loc, label: ordem.append("target") or True
        with mock.patch.object(vl, "vision_locate", return_value=self._loc_ok()), \
             mock.patch.object(vl, "OVERLAY_TARGET_CALLBACK", callback), \
             mock.patch.dict(sys.modules, {"pyautogui": fake}), \
             mock.patch("time.sleep", side_effect=lambda segundos: ordem.append("sleep")):
            resultado = vl.vision_click("alvo")
        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(ordem, ["target", "sleep", "click"])

    def test_sem_overlay_ativo_nao_adiciona_atraso(self):
        fake = PyAutoGUIFalso()
        with mock.patch.object(vl, "vision_locate", return_value=self._loc_ok()), \
             mock.patch.object(vl, "OVERLAY_TARGET_CALLBACK", None), \
             mock.patch.dict(sys.modules, {"pyautogui": fake}), \
             mock.patch("time.sleep") as dormir:
            resultado = vl.vision_click("alvo")
        self.assertEqual(resultado["status"], "ok")
        dormir.assert_not_called()

    def test_alvo_nao_encontrado_nao_clica(self):
        fake = PyAutoGUIFalso()
        loc = {"status": "ok", "encontrado": False, "result": "nada", "metodo": "none"}
        r = self._click(loc, fake)
        self.assertFalse(r.get("encontrado"))
        self.assertEqual(fake.chamadas, [], "nada pode ser clicado sem alvo encontrado")

    def test_status_erro_do_locate_nao_clica(self):
        fake = PyAutoGUIFalso()
        loc = {"status": "erro", "result": "Erro no OCR: x"}
        r = self._click(loc, fake)
        self.assertEqual(r["status"], "erro")
        self.assertEqual(fake.chamadas, [])

    def test_click_alvo_nao_encontrado_deveria_reportar_erro(self):
        """Um locate legado/incompleto nao pode fazer o clique parecer sucesso."""
        fake = PyAutoGUIFalso()
        loc = {"status": "ok", "encontrado": False, "result": "Nenhum elemento", "metodo": "none"}
        r = self._click(loc, fake)
        self.assertEqual(r["status"], "erro", f"esperado erro, veio {r}")

    def test_pyautogui_falha_devolve_erro_estruturado(self):
        fake = PyAutoGUIFalso(erro=RuntimeError("failsafe acionado"))
        r = self._click(self._loc_ok(), fake)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("failsafe", r["result"])

    def test_localizacao_sem_coordenadas_reporta_erro(self):
        """BUG: locate sem x/y -> vision_click devolve {'status':'ok', x: None, y: None}.

        Pior do que o alvo nao encontrado: o resultado diz ``ok`` e
        ``x: None``, ou seja, o executor do planner registra sucesso sem que
        nenhum clique com coordenada real tenha acontecido.
        """
        fake = PyAutoGUIFalso()
        r = self._click(self._loc_ok(x=None, y=None), fake)
        self.assertNotIn("x", r, f"nao pode reportar coordenada inexistente: {r}")
        self.assertNotIn("y", r)
        self.assertEqual(fake.chamadas_de("moveTo"), [])

    def test_localizacao_com_um_eixo_nulo_nao_move_o_rato(self):
        for x, y in [(None, 10), (10, None)]:
            fake = PyAutoGUIFalso()
            r = self._click(self._loc_ok(x=x, y=y), fake)
            self.assertIsInstance(r, dict)
            self.assertEqual(fake.chamadas_de("moveTo"), [],
                             f"nao pode mover o rato com coordenadas {x},{y}")

    def test_coordenadas_negativas_e_absurdas_sao_barradas_antes_do_clique(self):
        """Coordenadas fora da tela devem falhar sem chamar o mouse."""
        for x, y in [(-1, -1), (1920, 1080), (999999, 999999)]:
            fake = PyAutoGUIFalso()
            r = self._click(self._loc_ok(x=x, y=y), fake)
            self.assertEqual(r["status"], "erro", f"({x},{y}) -> {r}")
            self.assertEqual(fake.chamadas_de("click"), [],
                             f"({x},{y}) nao deveria chegar ao pyautogui")

    def test_coordenada_fora_do_ecra_e_barrada_antes_do_pyautogui(self):
        fake = PyAutoGUIEstrito()
        r = self._click(self._loc_ok(x=-1, y=-1), fake)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("Coordenadas invalidas", r["result"])
        self.assertEqual(fake.chamadas_de("click"), [])

    def test_locate_que_levanta_nao_escapa_do_vision_click(self):
        with mock.patch.object(vl, "vision_locate", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                vl.vision_click("alvo")

    def test_descricao_vazia_chega_ao_locate_e_devolve_erro(self):
        r = helpers.sem_excecao(vl.vision_click, "")
        self.assertTrue(helpers.eh_erro_estruturado(r))

    def test_descricao_so_espacos_nao_clica(self):
        fake = PyAutoGUIFalso()
        with mock.patch.dict(sys.modules, {"pyautogui": fake}):
            r = vl.vision_click("   ")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertEqual(fake.chamadas, [])


class VisionTypeTestCase(helpers.CasoBase):
    """``vision_type`` clica antes de digitar, respeita ``limpar`` e nao levanta."""

    def _type(self, loc_resultado, texto, limpar=True, pyautogui_falso=None):
        fake = pyautogui_falso or PyAutoGUIFalso()
        with mock.patch.object(vl, "vision_locate", return_value=loc_resultado), \
             mock.patch.dict(sys.modules, {"pyautogui": fake}), \
             mock.patch("time.sleep"):
            return vl.vision_type("alvo", texto, limpar), fake

    def _loc_ok(self, x=10, y=20, label="campo email"):
        return {"status": "ok", "encontrado": True, "x": x, "y": y, "label": label,
                "screenshot": "C:/tmp/ss.png", "metodo": "fuzzy", "conf": 0.9}

    def test_digita_texto_apos_clicar(self):
        r, fake = self._type(self._loc_ok(), "user@example.com")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["texto"], "user@example.com")
        self.assertEqual(fake.chamadas_de("click")[0][1], (10, 20))
        self.assertEqual(fake.chamadas_de("write")[0][1][0], "user@example.com")

    def test_limpar_true_faz_ctrl_a_e_delete(self):
        r, fake = self._type(self._loc_ok(), "novo", limpar=True)
        self.assertEqual(fake.chamadas_de("hotkey")[0][1], ("ctrl", "a"))
        self.assertEqual(fake.chamadas_de("press")[0][1], ("delete",))
        self.assertEqual(r["status"], "ok")

    def test_limpar_false_nao_apaga_campo(self):
        r, fake = self._type(self._loc_ok(), "append", limpar=False)
        self.assertEqual(fake.chamadas_de("hotkey"), [])
        self.assertEqual(fake.chamadas_de("press"), [])
        self.assertEqual(fake.chamadas_de("write")[0][1][0], "append")

    def test_texto_vazio_ainda_digita_string_vazia(self):
        r, fake = self._type(self._loc_ok(), "", limpar=True)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(fake.chamadas_de("write")[0][1][0], "")

    def test_texto_enorme_e_unicode_sao_repassados(self):
        texto = ("çãõ🎯" * 1250)[:5000]
        r, fake = self._type(self._loc_ok(), texto)
        self.assertEqual(len(fake.chamadas_de("write")[0][1][0]), len(texto))
        self.assertEqual(r["texto"], texto)

    def test_texto_com_caracteres_perigosos(self):
        for texto in ["; rm -rf /", "$(whoami)", "`id`", "\\n\\r", "\x1b[31m"]:
            r, fake = self._type(self._loc_ok(), texto)
            self.assertEqual(r["status"], "ok")
            self.assertEqual(fake.chamadas_de("write")[0][1][0], texto)

    def test_limpar_tipo_errado_truthy(self):
        for valor in [0, 1, "sim", "", None, []]:
            r, fake = self._type(self._loc_ok(), "x", limpar=valor)
            self.assertEqual(r["status"], "ok")
            esperado_limpeza = bool(valor)
            self.assertEqual(bool(fake.chamadas_de("hotkey")), esperado_limpeza, repr(valor))

    def test_alvo_nao_encontrado_nao_clica_nem_digita(self):
        fake = PyAutoGUIFalso()
        loc = {"status": "ok", "encontrado": False, "result": "nada", "metodo": "none"}
        r, fake = self._type(loc, "texto", pyautogui_falso=fake)
        self.assertFalse(r.get("encontrado"))
        self.assertEqual(fake.chamadas, [], "nao pode digitar sem alvo")

    def test_type_alvo_nao_encontrado_deveria_reportar_erro(self):
        """Um campo nao encontrado nao pode fazer a digitacao parecer sucesso."""
        loc = {"status": "ok", "encontrado": False, "result": "nada", "metodo": "none"}
        r, _fake = self._type(loc, "texto")
        self.assertEqual(r["status"], "erro", f"esperado erro, veio {r}")

    def test_erro_ao_digitar_devolve_erro_estruturado(self):
        fake = PyAutoGUIFalso(erro=RuntimeError("teclado ocupado"))
        r, _ = self._type(self._loc_ok(), "texto", pyautogui_falso=fake)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("teclado ocupado", r["result"])

    def test_texto_none_nao_levanta(self):
        fake = PyAutoGUIEstrito()
        r, _ = self._type(self._loc_ok(), None, pyautogui_falso=fake)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("Erro ao digitar", r["result"])
        self.assertEqual(fake.chamadas_de("write"), [], "nao deve digitar valor invalido")

    def test_descricao_vazia_devolve_erro_sem_digitar(self):
        fake = PyAutoGUIFalso()
        with mock.patch.dict(sys.modules, {"pyautogui": fake}):
            r = vl.vision_type("", "texto")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertEqual(fake.chamadas, [], "descricao vazia nao pode clicar nem digitar")


# ===========================================================================
# 4. computer/controller.py (pyautogui 100% mockado)
# ===========================================================================


class ControllerTestCase(helpers.CasoBase):
    """Contrato das 9 funcoes de mouse/teclado, sempre com pyautogui mockado."""

    def setUp(self):
        super().setUp()
        self.fake = PyAutoGUIFalso()
        self._patch = mock.patch.object(controller_mod, "pyautogui", self.fake)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        super().tearDown()

    # -- sucesso ------------------------------------------------------------
    def test_move_mouse_sucesso_e_chamada_correta(self):
        r = controller_mod.move_mouse(100, 200, duration=0.5)
        self.assertEqual(r["status"], "ok")
        self.assertIn("100", r["result"])
        self.assertEqual(self.fake.chamadas_de("moveTo")[0][1], (100, 200))
        self.assertEqual(self.fake.chamadas_de("moveTo")[0][2], {"duration": 0.5})

    def test_click_com_coordenadas_move_e_clica(self):
        r = controller_mod.click(10, 20)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("moveTo")[0][1], (10, 20))
        self.assertEqual(len(self.fake.chamadas_de("click")), 1)

    def test_click_sem_coordenadas_clica_na_posicao_atual(self):
        r = controller_mod.click()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("moveTo"), [])
        self.assertEqual(self.fake.chamadas_de("click")[0][2], {"button": "left"})

    def test_click_button_direito_e_repassado(self):
        controller_mod.click(button="right")
        self.assertEqual(self.fake.chamadas_de("click")[0][2], {"button": "right"})

    def test_double_click_e_right_click_sucesso(self):
        self.assertEqual(controller_mod.double_click(1, 2)["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("doubleClick").__len__(), 1)
        self.assertEqual(controller_mod.right_click(3, 4)["status"], "ok")
        self.assertEqual(len(self.fake.chamadas_de("rightClick")), 1)

    def test_type_text_repassa_intervalo_e_trunca_result(self):
        r = controller_mod.type_text("ola mundo", interval=0.01)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("write")[0][1], ("ola mundo",))
        self.assertEqual(self.fake.chamadas_de("write")[0][2], {"interval": 0.01})
        self.assertLessEqual(len(r["result"]), 100)

    def test_press_key_e_hotkey(self):
        self.assertEqual(controller_mod.press_key("enter")["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("press")[0][1], ("enter",))
        self.assertEqual(controller_mod.hotkey("ctrl", "shift", "s")["status"], "ok")
        self.assertEqual(self.fake.chamadas_de("hotkey")[0][1], ("ctrl", "shift", "s"))
        self.assertIn("ctrl+shift+s", controller_mod.hotkey("ctrl", "shift", "s")["result"])

    def test_scroll_positivo_e_negativo(self):
        for valor in [500, -500, 0]:
            r = controller_mod.scroll(valor)
            self.assertEqual(r["status"], "ok")
        quantias = [c[1][0] for c in self.fake.chamadas_de("scroll")]
        self.assertEqual(quantias, [500, -500, 0])

    # -- valores limite / tipos errados -------------------------------------
    def test_move_mouse_com_floats_negativos_e_grandes(self):
        for x, y in [(0, 0), (-1, -1), (999999, 999999), (1.5, 2.5), (-0.0, 0.0)]:
            r = controller_mod.move_mouse(x, y)
            self.assertEqual(r["status"], "ok", f"{x},{y}")

    def test_move_mouse_none_ou_string_devolve_erro_estruturado(self):
        estrito = PyAutoGUIEstrito()
        with mock.patch.object(controller_mod, "pyautogui", estrito):
            for x, y in [(None, None), ("a", "b"), (None, 10), ([], {})]:
                r = controller_mod.move_mouse(x, y)
                self.assertTrue(helpers.eh_erro_estruturado(r), f"{x},{y} -> {r}")
        self.assertEqual(estrito.chamadas, [], "nenhum movimento pode acontecer com tipo errado")

    def test_click_com_apenas_um_eixo_nao_move(self):
        for kwargs in [{"x": 10}, {"y": 20}, {"x": None, "y": None}]:
            self.fake.chamadas.clear()
            r = controller_mod.click(**kwargs)
            self.assertEqual(r["status"], "ok")
            self.assertEqual(self.fake.chamadas_de("moveTo"), [], str(kwargs))

    def test_coordenadas_fora_do_ecra_viraram_erro_estruturado(self):
        """A validacao de limites e delegada ao pyautogui; o erro nao escapa.

        Nao ha clamp proprio, mas o FailSafeException do pyautogui e convertido
        em {'status': 'erro'} (o bug de *ausencia* de validacao esta documentado
        em VisionClickTestCase.test_BUG_coordenadas_...).
        """
        estrito = PyAutoGUIEstrito()
        with mock.patch.object(controller_mod, "pyautogui", estrito):
            for x, y in [(-1, -1), (999999, 999999)]:
                r = controller_mod.move_mouse(x, y)
                self.assertTrue(helpers.eh_erro_estruturado(r), f"({x},{y}) -> {r}")
                self.assertIn("FailSafeException", r["result"])
        self.assertEqual(estrito.chamadas, [])

    def test_type_text_vazio_unicode_e_5000_chars(self):
        for texto in ["", "çãõ", "🎯🔥", "x" * 5000, "'; DROP TABLE t; --"]:
            r = controller_mod.type_text(texto)
            self.assertEqual(r["status"], "ok", repr(texto[:20]))

    def test_type_text_none_devolve_erro_estruturado(self):
        estrito = PyAutoGUIEstrito()
        with mock.patch.object(controller_mod, "pyautogui", estrito):
            r = controller_mod.type_text(None)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("TypeError", r["result"])
        self.assertEqual(estrito.chamadas, [])

    def test_press_key_vazia_devolve_erro_estruturado(self):
        class FalhaChave:
            def press(self, key):
                raise ValueError(f"tecla invalida: {key!r}")

        with mock.patch.object(controller_mod, "pyautogui", FalhaChave()):
            r = controller_mod.press_key("")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("tecla invalida", r["result"])

    def test_hotkey_sem_teclas_nao_levanta(self):
        r = controller_mod.hotkey()
        self.assertEqual(r["status"], "ok")

    def test_scroll_string_devolve_erro_estruturado(self):
        estrito = PyAutoGUIEstrito()
        with mock.patch.object(controller_mod, "pyautogui", estrito):
            r = controller_mod.scroll("muito")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("TypeError", r["result"])
        self.assertEqual(estrito.chamadas, [])

    def test_scroll_float_devolve_erro_estruturado(self):
        estrito = PyAutoGUIEstrito()
        with mock.patch.object(controller_mod, "pyautogui", estrito):
            r = controller_mod.scroll(1.5)
        self.assertTrue(helpers.eh_erro_estruturado(r))

    # -- erros do pyautogui nao escapam -------------------------------------
    def test_todas_as_funcoes_devolvem_erro_quando_pyautogui_falha(self):
        quebrado = PyAutoGUIFalso(erro=RuntimeError("failsafe"))
        with mock.patch.object(controller_mod, "pyautogui", quebrado):
            casos = [
                lambda: controller_mod.move_mouse(1, 2),
                lambda: controller_mod.click(1, 2),
                lambda: controller_mod.double_click(1, 2),
                lambda: controller_mod.right_click(1, 2),
                lambda: controller_mod.type_text("x"),
                lambda: controller_mod.press_key("enter"),
                lambda: controller_mod.hotkey("ctrl", "c"),
                lambda: controller_mod.scroll(10),
            ]
            for caso in casos:
                r = helpers.sem_excecao(caso)
                self.assertTrue(helpers.eh_erro_estruturado(r), r)
                self.assertIn("RuntimeError", r["result"])

    def test_erro_contem_nome_da_excecao(self):
        quebrado = PyAutoGUIFalso(erro=socket.timeout("timeout do SO"))
        with mock.patch.object(controller_mod, "pyautogui", quebrado):
            r = controller_mod.move_mouse(1, 2)
        self.assertIn("timeout", r["result"])


# ===========================================================================
# 5. computer/screen.py (mss mockado; nada e escrito no disco real)
# ===========================================================================


class ScreenTestCase(helpers.CasoBase):
    """``screen.screenshot`` usa a factory ``mss.mss()`` (patch dessa factory)."""

    def setUp(self):
        super().setUp()
        self.dir_ss = Path(self.tmp) / "shots"
        self.dir_ss.mkdir(parents=True, exist_ok=True)

    def test_screenshot_salvo_grava_png_e_devolve_path(self):
        fake = MSSFalso(ImgFalsa(1920, 1080))
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", return_value=fake), \
             mock.patch("mss.tools.to_png") as to_png:
            r = screen_mod.screenshot(salvar=True)
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["path"].startswith(str(self.dir_ss)))
        self.assertTrue(os.path.basename(r["path"]).startswith("screen_"))
        self.assertTrue(r["path"].endswith(".png"))
        to_png.assert_called_once()
        self.assertEqual(len(fake.grabs), 1, "deve capturar exatamente um monitor")

    def test_screenshot_nao_salvo_nao_grava_ficheiro(self):
        fake = MSSFalso()
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", return_value=fake), \
             mock.patch("mss.tools.to_png") as to_png:
            r = screen_mod.screenshot(salvar=False)
        self.assertEqual(r["status"], "ok")
        self.assertNotIn("path", r)
        to_png.assert_not_called()
        self.assertEqual(list(self.dir_ss.iterdir()), [])

    def test_screenshot_com_salvar_truthy_nao_bool(self):
        fake = MSSFalso()
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", return_value=fake), \
             mock.patch("mss.tools.to_png") as to_png:
            r = screen_mod.screenshot(salvar=1)
        self.assertEqual(r["status"], "ok")
        to_png.assert_called_once()
        self.assertIn("path", r)

    def test_screenshot_erro_do_mss_devolve_erro_estruturado(self):
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", side_effect=OSError("sem ecra")):
            r = screen_mod.screenshot()
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("OSError", r["result"])
        self.assertIn("sem ecra", r["result"])
        self.assertEqual(list(self.dir_ss.iterdir()), [])

    def test_screenshot_erro_no_grab_nao_deixa_ficheiro(self):
        fake = MSSFalso(erro=RuntimeError("monitor invalido"))
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", return_value=fake), \
             mock.patch("mss.tools.to_png") as to_png:
            r = screen_mod.screenshot()
        self.assertTrue(helpers.eh_erro_estruturado(r))
        to_png.assert_not_called()
        self.assertEqual(list(self.dir_ss.iterdir()), [])

    def test_screenshot_erro_ao_gravar_png_devolve_erro(self):
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss)), \
             mock.patch.object(mss_mod, "mss", return_value=MSSFalso()), \
             mock.patch("mss.tools.to_png", side_effect=PermissionError("disco cheio")):
            r = screen_mod.screenshot()
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("PermissionError", r["result"])

    def test_screenshot_nunca_levanta(self):
        with mock.patch.object(screen_mod, "SCREENSHOTS_DIR", str(self.dir_ss / "nao\\valido\x00")), \
             mock.patch.object(mss_mod, "mss", return_value=MSSFalso()):
            r = helpers.sem_excecao(screen_mod.screenshot)
        self.assertIsInstance(r, dict)
        self.assertIn(r["status"], ("ok", "erro"))


# ===========================================================================
# 6. computer/windows.py (pygetwindow + ctypes mockados)
# ===========================================================================


class WindowsTestCase(helpers.CasoBase):
    def test_get_windows_filtra_titulos_vazios(self):
        gw = JanelaFalsaGW(titulos=["Chrome", "", "   ", "Explorer"])
        with mock.patch.object(windows_mod, "gw", gw):
            r = windows_mod.get_windows()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["result"], ["Chrome", "Explorer"])

    def test_get_windows_lista_vazia(self):
        with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=[])):
            r = windows_mod.get_windows()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["result"], [])

    def test_get_windows_unicode_e_titulo_enorme(self):
        titulos = ["🎯 Janela çãõ", "x" * 5000, "'; DROP TABLE janelas; --"]
        with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=titulos)):
            r = windows_mod.get_windows()
        self.assertEqual(r["result"], titulos)

    def test_get_windows_erro_do_pygetwindow_nao_levanta(self):
        gw = JanelaFalsaGW(erro=RuntimeError("sem sessao grafica"))
        with mock.patch.object(windows_mod, "gw", gw):
            r = helpers.sem_excecao(windows_mod.get_windows)
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("RuntimeError", r["result"])

    def test_get_active_window_com_janela(self):
        with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(ativa=janela_falsa("VS Code"))):
            r = windows_mod.get_active_window()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["result"], "VS Code")

    def test_get_active_window_sem_janela(self):
        with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(ativa=None)):
            r = windows_mod.get_active_window()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["result"], "Nenhuma")

    def test_get_active_window_erro_nao_levanta(self):
        with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(erro=OSError("sem win32"))):
            r = helpers.sem_excecao(windows_mod.get_active_window)
        self.assertTrue(helpers.eh_erro_estruturado(r))

    # -- _focus_by_title_ctypes --------------------------------------------
    def _ctypes_ok(self, janelas, visivel=True, iconic=False):
        u = user32_falso(janelas, visivel=visivel, iconic=iconic)
        enumwindows_executor(u, janelas)
        return [
            mock.patch.object(windows_mod, "user32", u),
            mock.patch.object(windows_mod.ctypes, "WINFUNCTYPE", lambda *a, **k: (lambda f: f)),
        ]

    def test_focus_por_ctypes_encontra_case_insensitive(self):
        janelas = [(1, "Bloco de Notas"), (2, "Google Chrome")]
        patches = self._ctypes_ok(janelas)
        for p in patches:
            p.start()
        try:
            achou = windows_mod._focus_by_title_ctypes("google")
            u = windows_mod.user32
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertTrue(achou)
        u.SetForegroundWindow.assert_called_once_with(2)
        u.ShowWindow.assert_called_once_with(2, windows_mod.SW_SHOW)

    def test_focus_por_ctypes_restaura_janela_minimizada(self):
        janelas = [(7, "Calculadora")]
        patches = self._ctypes_ok(janelas, iconic=True)
        for p in patches:
            p.start()
        try:
            achou = windows_mod._focus_by_title_ctypes("calculadora")
            u = windows_mod.user32
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertTrue(achou)
        chamadas = [c[0][1] for c in u.ShowWindow.call_args_list]
        self.assertIn(windows_mod.SW_RESTORE, chamadas)

    def test_focus_por_ctypes_ignora_janelas_invisiveis(self):
        janelas = [(3, "Alvo invisivel")]
        patches = self._ctypes_ok(janelas, visivel=False)
        for p in patches:
            p.start()
        try:
            achou = windows_mod._focus_by_title_ctypes("alvo")
            u = windows_mod.user32
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertFalse(achou)
        u.SetForegroundWindow.assert_not_called()

    def test_focus_por_ctypes_titulo_vazio_nao_levanta(self):
        janelas = [(1, "Chrome")]
        patches = self._ctypes_ok(janelas)
        for p in patches:
            p.start()
        try:
            r = helpers.sem_excecao(windows_mod.focus_window, "")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertIsInstance(r, dict)
        self.assertIn(r["status"], ("ok", "erro"))

    def test_focus_por_ctypes_none_levanta_e_cai_no_fallback(self):
        """Titulo None: ``.lower()`` dentro do callback levanta AttributeError.

        O callback e chamado pelo Windows (aqui pelo fake), pelo que a excecao
        sai de ``_focus_by_title_ctypes`` e e apanhada por ``focus_window``.
        """
        janelas = [(1, "Chrome")]
        patches = self._ctypes_ok(janelas)
        for p in patches:
            p.start()
        try:
            with mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=["Chrome"])):
                r = helpers.sem_excecao(windows_mod.focus_window, None)
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertIn(r["status"], ("ok", "erro"))

    # -- focus_window -------------------------------------------------------
    def test_focus_window_sucesso_por_ctypes(self):
        janelas = [(5, "Visual Studio Code")]
        patches = self._ctypes_ok(janelas)
        for p in patches:
            p.start()
        try:
            r = windows_mod.focus_window("visual studio")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(r["status"], "ok")
        self.assertIn("visual studio", r["result"])

    def test_focus_window_fallback_pygetwindow(self):
        janelas = [(1, "Chrome")]  # ctypes nao encontra "firefox"
        patches = self._ctypes_ok(janelas)
        gw = JanelaFalsaGW(titulos=["Mozilla Firefox"])
        patches.append(mock.patch.object(windows_mod, "gw", gw))
        for p in patches:
            p.start()
        try:
            r = windows_mod.focus_window("firefox")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(r["status"], "ok")
        self.assertIn("fallback", r["result"])
        self.assertEqual(len(gw.activates), 1)

    def test_focus_window_fallback_restaura_minimizada(self):
        janelas = [(1, "Chrome")]
        patches = self._ctypes_ok(janelas)
        gw = JanelaFalsaGW(titulos=["Mozilla Firefox"])
        patches.append(mock.patch.object(windows_mod, "gw", gw))
        for p in patches:
            p.start()
        try:
            r = windows_mod.focus_window("firefox")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertIn(r["status"], ("ok", "erro"))
        self.assertIn("fallback", r["result"])

    def test_focus_window_nao_encontrada_devolve_erro(self):
        janelas = [(1, "Chrome")]
        patches = self._ctypes_ok(janelas)
        patches.append(mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=["Chrome"])))
        for p in patches:
            p.start()
        try:
            r = windows_mod.focus_window("janela que nao existe")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("nao encontrada", r["result"])

    def test_focus_window_fallback_com_erro_nao_levanta(self):
        janelas = [(1, "Chrome")]
        patches = self._ctypes_ok(janelas)
        patches.append(mock.patch.object(windows_mod, "gw", JanelaFalsaGW(erro=RuntimeError("boom"))))
        for p in patches:
            p.start()
        try:
            r = helpers.sem_excecao(windows_mod.focus_window, "firefox")
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("RuntimeError", r["result"])

    def test_focus_window_com_erro_no_ctypes_nao_levanta(self):
        with mock.patch.object(windows_mod, "_focus_by_title_ctypes", side_effect=OSError("win32 morreu")), \
             mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=["Chrome"])):
            r = helpers.sem_excecao(windows_mod.focus_window, "chrome")
        self.assertTrue(helpers.eh_erro_estruturado(r))

    def test_focus_window_titulo_enorme_unicode_e_perigoso(self):
        titulos = ["x" * 5000, "🎯", "'; DROP TABLE w; --", "a\nb"]
        for titulo in titulos:
            with mock.patch.object(windows_mod, "_focus_by_title_ctypes", return_value=False), \
                 mock.patch.object(windows_mod, "gw", JanelaFalsaGW(titulos=["Nada"])):
                r = helpers.sem_excecao(windows_mod.focus_window, titulo)
            self.assertIsInstance(r, dict)
            self.assertIn(r["status"], ("ok", "erro"))


# ===========================================================================
# 7. Rotas /vision_locate, /vision_click, /vision_type (TestClient)
# ===========================================================================


@unittest.skipUnless(AGENT_DISPONIVEL, f"agent.py indisponivel: {MOTIVO_AGENT}")
class RotasVisionTestCase(helpers.CasoBase):
    """Contrato HTTP das rotas, com as funcoes de visao mockadas (sem servico real)."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        cls.client = TestClient(agent_mod.app)

    def setUp(self):
        super().setUp()
        self._ws = workspace_temporario(agent_mod)
        self._ws.__enter__()

    def tearDown(self):
        self._ws.__exit__(None, None, None)
        super().tearDown()

    # -- /vision_locate -----------------------------------------------------
    def test_vision_locate_sucesso(self):
        resposta = {"status": "ok", "encontrado": True, "x": 10, "y": 20,
                    "label": "New Chat", "metodo": "fuzzy"}
        with mock.patch.object(vl, "vision_locate", return_value=resposta) as fn:
            r = self.client.post("/vision_locate", json={"descricao": "New Chat"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), resposta)
        fn.assert_called_once_with("New Chat", None)

    def test_vision_locate_repassa_screenshot_path(self):
        with mock.patch.object(vl, "vision_locate", return_value={"status": "ok"}) as fn:
            r = self.client.post(
                "/vision_locate",
                json={"descricao": "New Chat", "screenshot_path": "C:/tmp/a.png"},
            )
        self.assertEqual(r.status_code, 200)
        fn.assert_called_once_with("New Chat", "C:/tmp/a.png")

    def test_vision_locate_descricao_vazia_422(self):
        r = self.client.post("/vision_locate", json={"descricao": ""})
        self.assertEqual(r.status_code, 422)
        self.assertIn("descricao", json.dumps(r.json()))

    def test_vision_locate_sem_descricao_422(self):
        r = self.client.post("/vision_locate", json={})
        self.assertEqual(r.status_code, 422)

    def test_vision_locate_descricao_so_espacos_nao_500(self):
        with mock.patch.object(vl, "vision_locate",
                               return_value={"status": "erro", "result": "Descricao vazia"}) as fn:
            r = self.client.post("/vision_locate", json={"descricao": "   "})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")
        fn.assert_called_once()

    def test_vision_locate_descricao_201_chars_422(self):
        r = self.client.post("/vision_locate", json={"descricao": "x" * 201})
        self.assertEqual(r.status_code, 422)
        r2 = self.client.post("/vision_locate", json={"descricao": "x" * 200})
        self.assertNotEqual(r2.status_code, 422)

    def test_vision_locate_unicode_e_emoji_aceitos(self):
        with mock.patch.object(vl, "vision_locate", return_value={"status": "ok"}) as fn:
            r = self.client.post("/vision_locate", json={"descricao": "botão 🎯 çãõ"})
        self.assertEqual(r.status_code, 200)
        fn.assert_called_once_with("botão 🎯 çãõ", None)

    def test_vision_locate_tipos_errados_422(self):
        for payload in [{"descricao": 123}, {"descricao": None}, {"descricao": ["a"]},
                        {"descricao": {"x": 1}}, {"descricao": True},
                        {"descricao": "x", "screenshot_path": 5}]:
            r = self.client.post("/vision_locate", json=payload)
            self.assertEqual(r.status_code, 422, payload)

    def test_vision_locate_corpo_nao_json_422(self):
        r = self.client.post("/vision_locate", content=b"isto nao e json",
                             headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 422)

    def test_vision_locate_excecao_interna_vira_erro_200(self):
        with mock.patch.object(vl, "vision_locate", side_effect=RuntimeError("ocr morreu")):
            r = self.client.post("/vision_locate", json={"descricao": "New Chat"})
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("RuntimeError", corpo["result"])
        self.assertIn("ocr morreu", corpo["result"])

    # -- /vision_click ------------------------------------------------------
    def test_vision_click_sucesso(self):
        resposta = {"status": "ok", "x": 1, "y": 2, "label": "ok"}
        with mock.patch.object(vl, "vision_click", return_value=resposta) as fn:
            r = self.client.post("/vision_click", json={"descricao": "Enviar"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), resposta)
        fn.assert_called_once_with("Enviar")

    def test_vision_click_nao_aceita_screenshot_path(self):
        """A rota ignora screenshot_path: o clique deve usar o locate interno."""
        with mock.patch.object(vl, "vision_click", return_value={"status": "ok"}) as fn:
            r = self.client.post("/vision_click",
                                 json={"descricao": "Enviar", "screenshot_path": "C:/tmp/x.png"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(fn.call_args[0], ("Enviar",))

    def test_vision_click_descricao_em_falta_422(self):
        self.assertEqual(self.client.post("/vision_click", json={}).status_code, 422)
        self.assertEqual(self.client.post("/vision_click", json={"descricao": ""}).status_code, 422)

    def test_vision_click_excecao_interna_vira_erro_200(self):
        with mock.patch.object(vl, "vision_click", side_effect=ValueError("coordenada invalida")):
            r = self.client.post("/vision_click", json={"descricao": "Enviar"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")
        self.assertIn("ValueError", r.json()["result"])

    def test_vision_click_alvo_nao_encontrado_nao_500(self):
        with mock.patch.object(vl, "vision_click",
                               return_value={"status": "ok", "encontrado": False, "metodo": "none"}):
            r = self.client.post("/vision_click", json={"descricao": "nao existe"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["encontrado"])

    # -- /vision_type -------------------------------------------------------
    def test_vision_type_sucesso_com_limpar_default(self):
        with mock.patch.object(vl, "vision_type",
                               return_value={"status": "ok", "texto": "abc"}) as fn:
            r = self.client.post("/vision_type",
                                 json={"descricao": "campo", "texto": "abc"})
        self.assertEqual(r.status_code, 200)
        fn.assert_called_once_with("campo", "abc", True)

    def test_vision_type_repassa_limpar_false(self):
        with mock.patch.object(vl, "vision_type", return_value={"status": "ok"}) as fn:
            r = self.client.post("/vision_type",
                                 json={"descricao": "campo", "texto": "abc", "limpar": False})
        self.assertEqual(r.status_code, 200)
        fn.assert_called_once_with("campo", "abc", False)

    def test_vision_type_sem_texto_422(self):
        r = self.client.post("/vision_type", json={"descricao": "campo"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("texto", json.dumps(r.json()))

    def test_vision_type_texto_vazio_aceito(self):
        with mock.patch.object(vl, "vision_type", return_value={"status": "ok"}) as fn:
            r = self.client.post("/vision_type", json={"descricao": "campo", "texto": ""})
        self.assertEqual(r.status_code, 200)
        fn.assert_called_once_with("campo", "", True)

    def test_vision_type_texto_5000_ok_e_5001_422(self):
        with mock.patch.object(vl, "vision_type", return_value={"status": "ok"}):
            r = self.client.post("/vision_type",
                                 json={"descricao": "campo", "texto": "x" * 5000})
        self.assertEqual(r.status_code, 200)
        r2 = self.client.post("/vision_type",
                              json={"descricao": "campo", "texto": "x" * 5001})
        self.assertEqual(r2.status_code, 422)

    def test_vision_type_texto_unicode_emoji_e_perigoso(self):
        for texto in ["🎯 çãõ", "'; DROP TABLE t; --", "<script>x</script>", "\x00\x1b"]:
            with mock.patch.object(vl, "vision_type", return_value={"status": "ok"}) as fn:
                r = self.client.post("/vision_type", json={"descricao": "campo", "texto": texto})
            self.assertEqual(r.status_code, 200, repr(texto))
            fn.assert_called_once_with("campo", texto, True)

    def test_vision_type_limpar_tipo_errado_422(self):
        for valor in ["sim", None, [], {}]:
            r = self.client.post("/vision_type",
                                 json={"descricao": "campo", "texto": "x", "limpar": valor})
            self.assertEqual(r.status_code, 422, repr(valor))

    def test_vision_type_limpar_numerico_e_coagido_para_bool(self):
        """pydantic aceita 0/1 como bool; 0 -> False e 1 -> True."""
        for entrada, esperado in [(0, False), (1, True)]:
            with mock.patch.object(vl, "vision_type", return_value={"status": "ok"}) as fn:
                r = self.client.post("/vision_type",
                                     json={"descricao": "campo", "texto": "x",
                                           "limpar": entrada})
            self.assertEqual(r.status_code, 200, repr(entrada))
            fn.assert_called_once_with("campo", "x", esperado)

    def test_vision_type_excecao_interna_vira_erro_200(self):
        with mock.patch.object(vl, "vision_type", side_effect=RuntimeError("teclado morto")):
            r = self.client.post("/vision_type", json={"descricao": "campo", "texto": "x"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")
        self.assertIn("teclado morto", r.json()["result"])

    def test_rotas_vision_com_metodo_errado_405(self):
        for rota in ["/vision_locate", "/vision_click", "/vision_type"]:
            self.assertEqual(self.client.get(rota).status_code, 405, rota)

    # -- integracao real das funcoes (mss/ocr mockados, sem servico) --------
    def test_rota_vision_locate_pipeline_real_com_mocks(self):
        """A rota chama a funcao REAL de vision_locate; screenshot/OCR mockados."""
        elementos = [{"label": "New Chat", "bbox": [100, 200, 140, 220], "conf": 0.97}]
        dir_tmp = Path(self.tmp) / "ss"
        dir_tmp.mkdir(parents=True, exist_ok=True)
        with mock.patch.object(vl, "_screenshot",
                               return_value={"path": str(dir_tmp / "a.png"), "width": 1, "height": 1}), \
             mock.patch.object(vl, "_ocr", return_value=elementos):
            r = self.client.post("/vision_locate", json={"descricao": "New Chat"})
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual(corpo["status"], "ok")
        self.assertTrue(corpo["encontrado"])
        self.assertEqual((corpo["x"], corpo["y"]), (120, 210))

    def test_rota_vision_type_pipeline_real_nao_usa_servico_externo(self):
        elementos = [{"label": "campo email", "bbox": [0, 0, 20, 20], "conf": 0.9}]
        fake_pyautogui = PyAutoGUIFalso()
        fake_pyautogui.size = lambda: type("Size", (), {"width": 100, "height": 100})()
        with mock.patch.object(vl, "_screenshot",
                               return_value={"path": "C:/tmp/a.png", "width": 100, "height": 100}), \
             mock.patch.object(vl, "_ocr", return_value=elementos), \
             mock.patch.dict(sys.modules, {"pyautogui": fake_pyautogui}), \
             mock.patch("time.sleep"):
            r = self.client.post("/vision_type",
                                 json={"descricao": "campo email", "texto": "a@b.c",
                                       "limpar": False})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(fake_pyautogui.chamadas_de("write")[0][1][0], "a@b.c")

    def test_rota_vision_locate_sem_textos_na_tela(self):
        with mock.patch.object(vl, "_screenshot",
                               return_value={"path": "C:/tmp/a.png", "width": 1, "height": 1}), \
             mock.patch.object(vl, "_ocr", return_value=[]):
            r = self.client.post("/vision_locate", json={"descricao": "qualquer"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")
        self.assertFalse(r.json()["encontrado"])


# ===========================================================================
# 8. Isolamento: nada de rede real nos caminhos testados
# ===========================================================================


class SemEfeitosColateraisTestCase(helpers.CasoBase):
    """Garante que os caminhos de rede/IO sao bloqueados e nao levantam."""

    def test_llm_escolher_nao_abre_socket(self):
        candidatos = [{"label": "Sign In", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        with sem_rede():
            resultado = vl._llm_escolher("login", candidatos)
        self.assertIsNone(resultado)

    def test_vision_locate_ambiguo_sem_rede_nao_levanta(self):
        elementos = [{"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        with sem_rede(), \
             mock.patch.object(vl, "_screenshot",
                               return_value={"path": "C:/tmp/a.png", "width": 1, "height": 1}), \
             mock.patch.object(vl, "_ocr", return_value=elementos):
            r = helpers.sem_excecao(vl.vision_locate, "Entrar")
        self.assertEqual(r["status"], "erro")
        self.assertFalse(r["encontrado"])
        self.assertEqual(r["metodo"], "none")

    def test_vision_click_com_sem_rede_nao_clica_em_alvo_real(self):
        elementos = [{"label": "Entrar agora", "bbox": [0, 0, 10, 10], "conf": 0.9}]
        fake = PyAutoGUIFalso()
        with sem_rede(), \
             mock.patch.object(vl, "_screenshot",
                               return_value={"path": "C:/tmp/a.png", "width": 1, "height": 1}), \
             mock.patch.object(vl, "_ocr", return_value=elementos), \
             mock.patch.dict(sys.modules, {"pyautogui": fake}):
            r = helpers.sem_excecao(vl.vision_click, "Entrar")
        self.assertEqual(fake.chamadas, [], "nao pode clicar quando o alvo e ambiguo e o LLM falha")
        self.assertFalse(r["encontrado"])

    def test_screenshot_real_do_vision_nunca_e_chamado_com_mss_inexistente(self):
        """Se mss falhar, vision_locate devolve erro em vez de propagar."""
        with mock.patch.object(vl, "SCREENSHOTS_DIR", str(Path(self.tmp) / "ss")), \
             mock.patch.object(mss_mod, "MSS", side_effect=OSError("sem servidor grafico")):
            r = helpers.sem_excecao(vl.vision_locate, "New Chat")
        self.assertTrue(helpers.eh_erro_estruturado(r))
        self.assertIn("sem servidor grafico", r["result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
