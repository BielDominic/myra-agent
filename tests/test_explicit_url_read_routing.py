# -*- coding: utf-8 -*-
import unittest
from tasks import simple_task


class ExplicitUrlReadRoutingTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update({
            "browser_new_tab": lambda **kwargs: kwargs,
            "browser_read_active_tab": lambda **kwargs: kwargs,
            "browser_wait": lambda **kwargs: kwargs,
            "browser_click_text": lambda **kwargs: kwargs,
        })

    def tearDown(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self.original)

    def test_opens_explicit_url_only_once(self):
        goal = "Abra uma nova aba do Chrome em https://example.com, leia o título da página e informe o título."
        first = simple_task._decidir_proximo_passo(goal, [])
        self.assertEqual(first["ferramenta"], "browser_new_tab")
        self.assertEqual(first["args"]["url"], "https://example.com")
        history = [{"ferramenta": "browser_new_tab", "args": {"url": "https://example.com"}, "ok": True}]
        second = simple_task._decidir_proximo_passo(goal, history)
        self.assertEqual(second["ferramenta"], "browser_read_active_tab")
        self.assertEqual(second["args"]["url_contains"], "example.com")
        self.assertNotEqual(second["ferramenta"], "browser_new_tab")

    def test_finishes_after_successful_read(self):
        goal = "Abra uma nova aba do Chrome em https://example.com, leia o título da página e informe o título."
        history = [
            {"ferramenta": "browser_new_tab", "args": {"url": "https://example.com"}, "ok": True},
            {"ferramenta": "browser_read_active_tab", "args": {"url_contains": "example.com"}, "ok": True,
             "resultado": {"title": "Example Domain", "url": "https://example.com/"}},
        ]
        result = simple_task._decidir_proximo_passo(goal, history)
        self.assertEqual(result["acao"], "finalizar")
        self.assertIn("Example Domain", result["resultado"])

    def test_explicit_wait_uses_bounded_browser_wait(self):
        result = simple_task._decidir_proximo_passo("Aguarde 8 segundos e informe quando terminar.", [])
        self.assertEqual(result["ferramenta"], "browser_wait")
        self.assertEqual(result["args"]["ms"], 8000)

    def test_reads_active_tab_explicitly_without_opening_another_tab(self):
        goal = "Leia a aba ativa do Chrome e informe o título e os resultados visíveis."
        result = simple_task._decidir_proximo_passo(goal, [])
        self.assertEqual(result["ferramenta"], "browser_read_active_tab")
        self.assertEqual(result["args"], {})
        self.assertNotEqual(result["ferramenta"], "browser_new_tab")

    def test_read_only_browser_tools_keep_evidence_observer(self):
        self.assertTrue(simple_task._deve_observar("browser_read_active_tab"))
        self.assertTrue(simple_task._deve_observar("browser_read_page"))

    def test_easy_apply_opens_exact_job_tab_before_reading(self):
        goal = "Abra https://www.linkedin.com/jobs/view/123 e clique na candidatura simplificada para abrir o formulário."
        result = simple_task._decidir_proximo_passo(goal, [])
        self.assertEqual(result["ferramenta"], "browser_new_tab")
        self.assertEqual(result["args"]["url"], "https://www.linkedin.com/jobs/view/123")

    def test_easy_apply_click_targets_the_tab_id_returned_by_new_tab(self):
        goal = "Abra https://www.linkedin.com/jobs/view/123 e clique na candidatura simplificada para abrir o formulário."
        history = [
            {"ferramenta": "browser_new_tab", "args": {"url": "https://www.linkedin.com/jobs/view/123"},
             "ok": True, "resultado": {"tabId": 77, "url": "https://www.linkedin.com/jobs/view/123"}},
            {"ferramenta": "browser_read_active_tab", "args": {"tab_id": 77}, "ok": True,
             "resultado": {"title": "Kitchen Porter", "url": "https://www.linkedin.com/jobs/view/123",
                           "buttons": ["Candidatar-se"]}},
        ]
        result = simple_task._decidir_proximo_passo(goal, history)
        self.assertEqual(result["ferramenta"], "browser_click_text")
        self.assertEqual(result["args"]["tab_id"], 77)
        self.assertEqual(result["args"]["text"], "Candidatar-se")

    def test_easy_apply_reads_first_form_step_after_click(self):
        goal = "Abra https://www.linkedin.com/jobs/view/123 e clique na candidatura simplificada para abrir o formulário."
        history = [
            {"ferramenta": "browser_new_tab", "ok": True, "resultado": {"tabId": 77}},
            {"ferramenta": "browser_read_active_tab", "ok": True, "resultado": {"title": "Kitchen Porter"}},
            {"ferramenta": "browser_click_text", "ok": True, "resultado": {"clicked": "Candidatar-se"}},
        ]
        result = simple_task._decidir_proximo_passo(goal, history)
        self.assertEqual(result["ferramenta"], "browser_read_active_tab")
        self.assertEqual(result["args"]["tab_id"], 77)

    def test_does_not_trigger_for_open_only(self):
        result = simple_task._decidir_proximo_passo("Abra https://example.com", [])
        self.assertNotEqual(result.get("motivo"), "abrir a URL solicitada uma unica vez no Chrome conectado")


if __name__ == "__main__":
    unittest.main()
