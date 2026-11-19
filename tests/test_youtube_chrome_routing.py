# -*- coding: utf-8 -*-
import unittest
from urllib.parse import urlparse, parse_qs

from tasks import simple_task


class YouTubeChromeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS["browser_new_tab"] = lambda **kwargs: kwargs

    def tearDown(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self.original)

    def test_open_youtube_search_exact_term_in_single_chrome_tab(self):
        result = simple_task._decidir_proximo_passo(
            "abra o youtube e pesquise ALEE", []
        )
        self.assertEqual(result["ferramenta"], "browser_new_tab")
        parsed = urlparse(result["args"]["url"])
        self.assertEqual(parsed.netloc, "www.youtube.com")
        self.assertEqual(parse_qs(parsed.query)["search_query"], ["ALEE"])

    def test_does_not_trigger_without_youtube(self):
        result = simple_task._decidir_proximo_passo(
            "pesquise ALEE na internet", []
        )
        self.assertNotEqual(result.get("motivo", ""), "abrir a pesquisa solicitada diretamente em uma unica aba do Chrome conectado")

    def test_does_not_reopen_search_after_first_step(self):
        result = simple_task._decidir_proximo_passo(
            "abra o youtube e pesquise ALEE",
            [{"ferramenta": "browser_new_tab", "ok": True, "args": {"url": "x"}}],
        )
        self.assertNotEqual(result.get("motivo", ""), "abrir a pesquisa solicitada diretamente em uma unica aba do Chrome conectado")


if __name__ == "__main__":
    unittest.main()
