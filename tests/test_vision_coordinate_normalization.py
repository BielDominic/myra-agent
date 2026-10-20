"""Regressoes para conversao de coordenadas MSS -> PyAutoGUI (DPI)."""
from __future__ import annotations

import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from computer import vision_locate as vl


class PyAutoGUISimulado:
    def __init__(self, width=1280, height=720):
        self._size = SimpleNamespace(width=width, height=height)
        self.cliques = []

    def size(self):
        return self._size

    def click(self, *coords):
        self.cliques.append(coords)


class CoordenadasVisionTestCase(unittest.TestCase):
    def test_escala_pixels_fisicos_para_resolucao_logica(self):
        fake = PyAutoGUISimulado(1280, 720)
        loc = {"x": 960, "y": 540, "screen_width": 1920, "screen_height": 1080}
        self.assertEqual(vl._coordenadas_para_mouse(loc, fake), (640, 360))

    def test_preserva_contrato_antigo_sem_metadados(self):
        fake = PyAutoGUISimulado()
        self.assertEqual(vl._coordenadas_para_mouse({"x": 123, "y": 45}, fake), (123, 45))

    def test_recusa_coordenadas_fora_da_captura(self):
        fake = PyAutoGUISimulado()
        loc = {"x": 1920, "y": 10, "screen_width": 1920, "screen_height": 1080}
        self.assertIsNone(vl._coordenadas_para_mouse(loc, fake))

    def test_recusa_resolucao_de_mouse_invalida(self):
        fake = PyAutoGUISimulado(0, 0)
        loc = {"x": 10, "y": 10, "screen_width": 100, "screen_height": 100}
        self.assertIsNone(vl._coordenadas_para_mouse(loc, fake))

    def test_vision_click_usa_coordenadas_normalizadas(self):
        fake = PyAutoGUISimulado(1280, 720)
        loc = {
            "status": "ok", "encontrado": True, "x": 960, "y": 540,
            "screen_width": 1920, "screen_height": 1080,
            "label": "Enviar", "screenshot": "fake.png", "metodo": "fuzzy",
        }
        with mock.patch.object(vl, "vision_locate", return_value=loc), \
             mock.patch.dict(sys.modules, {"pyautogui": fake}), \
             mock.patch.object(vl, "_notificar_alvo_overlay", return_value=False):
            result = vl.vision_click("Enviar")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.cliques, [(640, 360)])
        # A resposta conserva coordenadas da captura para o overlay/debug.
        self.assertEqual((result["x"], result["y"]), (960, 540))


if __name__ == "__main__":
    unittest.main()
