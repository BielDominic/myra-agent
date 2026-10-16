# -*- coding: utf-8 -*-
"""Tests of screenshot-backed observation, without a display or model."""
import json
import unittest
from unittest import mock

from computer import observer


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.body


class VisualObserverTestCase(unittest.TestCase):
    def test_screenshot_is_sent_to_local_vision_endpoint(self):
        captured = {}
        def fake_urlopen(req, timeout=0):
            captured["url"] = req.full_url
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return FakeResponse({
                "choices": [{
                    "message": {
                        "content": '{"sucesso": true, "objetivo_atingido": true, "motivo": "tela confirma"}'
                    }
                }]
            })

        with mock.patch.object(observer, "SCREENSHOT_ENABLED", True), \
             mock.patch.object(observer, "_capturar_screenshot_base64", return_value="ZmFrZS1wbmc="), \
             mock.patch.object(observer.urllib.request, "urlopen", fake_urlopen):
            resultado = observer.observar(
                "abrir o GitHub", {"ferramenta": "browser_new_tab", "resultado": "aba aberta"}
            )

        self.assertEqual(captured["url"], observer.LLM_EYES_URL)
        content = captured["payload"]["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertTrue(resultado["objetivo_atingido"])
        self.assertIn("tela confirma", resultado["motivo"])

    def test_falha_visual_usa_fallback_textual(self):
        chamadas = []
        def fake_urlopen(req, timeout=0):
            chamadas.append(req.full_url)
            if req.full_url == observer.LLM_EYES_URL:
                raise OSError("vision offline")
            return FakeResponse({
                "message": {"content": '{"sucesso": true, "objetivo_atingido": false, "motivo": "nao concluiu"}'}
            })

        with mock.patch.object(observer, "SCREENSHOT_ENABLED", True), \
             mock.patch.object(observer, "_capturar_screenshot_base64", return_value="ZmFrZS1wbmc="), \
             mock.patch.object(observer.urllib.request, "urlopen", fake_urlopen):
            resultado = observer.observar("enviar email", {"ferramenta": "email_send"})

        self.assertEqual(chamadas, [observer.LLM_EYES_URL, observer.OLLAMA_URL])
        self.assertFalse(resultado["objetivo_atingido"])
        self.assertTrue(resultado["sucesso"])


if __name__ == "__main__":
    unittest.main()
