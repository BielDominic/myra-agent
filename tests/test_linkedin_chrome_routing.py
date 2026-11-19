import unittest
from urllib.parse import urlparse, parse_qs

from tasks import simple_task


class LinkedInChromeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update({
            "browser_new_tab": lambda **kwargs: kwargs,
            "browser_read_active_tab": lambda **kwargs: kwargs,
            "browser_click_text": lambda **kwargs: kwargs,
        })

    def tearDown(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self.original)

    def test_linkedin_job_search_opens_dedicated_part_time_search(self):
        result = simple_task._decidir_proximo_passo(
            "Procure vagas no LinkedIn para Healthcare Assistant em Longford e aplique a uma."
            , []
        )
        self.assertEqual(result["ferramenta"], "browser_new_tab")
        parsed = urlparse(result["args"]["url"])
        self.assertEqual(parsed.netloc, "www.linkedin.com")
        self.assertEqual(parsed.path, "/jobs/search/")
        query = parse_qs(parsed.query)
        self.assertIn("Healthcare Assistant", query["keywords"][0])
        self.assertIn("Home Care Assistant", query["keywords"][0])
        self.assertEqual(query["location"], ["Longford, Ireland"])
        self.assertEqual(query["f_JT"], ["P"])

    def test_does_not_trigger_without_linkedin(self):
        result = simple_task._decidir_proximo_passo(
            "Procure vagas de Healthcare Assistant em Longford", []
        )
        self.assertNotEqual(
            result.get("motivo"),
            "abrir uma unica busca do LinkedIn para vagas part-time de Healthcare/Home Care Assistant na regiao de Longford",
        )

    def test_does_not_open_duplicate_search_after_first_action(self):
        objective = "Procure vagas no LinkedIn para Healthcare Assistant em Longford."
        first = simple_task._decidir_proximo_passo(objective, [])
        result = simple_task._decidir_proximo_passo(
            objective,
            [{"passo": 1, "ferramenta": "browser_new_tab", "ok": True, "args": first["args"],
              "resultado": {"status": "ok", "tabId": 123}}],
        )
        self.assertNotEqual(
            result.get("motivo"),
            "abrir uma unica busca do LinkedIn para vagas part-time de Healthcare/Home Care Assistant na regiao de Longford",
        )


    def test_search_results_open_job_detail_before_easy_apply(self):
        objective = "Procure vagas no LinkedIn para Healthcare Assistant em Longford. Se houver Easy Apply, abra o formulário."
        search = simple_task._decidir_proximo_passo(objective, [])
        opened_search = {
            "passo": 1, "ferramenta": "browser_new_tab", "ok": True,
            "args": search["args"], "resultado": {"status": "ok", "tabId": 101},
        }
        read_search = {
            "passo": 2, "ferramenta": "browser_read_active_tab", "ok": True,
            "args": {"tab_id": 101},
            "resultado": {
                "status": "ok", "url": "https://www.linkedin.com/jobs/search/?keywords=Healthcare",
                "links": [{"href": "https://www.linkedin.com/jobs/view/12345/",
                           "text": "Healthcare Assistant - Part-time"}],
                "buttons": [],
            },
        }
        open_job = simple_task._decidir_proximo_passo(objective, [opened_search, read_search])
        self.assertEqual(open_job["ferramenta"], "browser_new_tab")
        self.assertEqual(open_job["args"]["url"], "https://www.linkedin.com/jobs/view/12345/")

    def test_job_detail_is_read_before_easy_apply_click(self):
        objective = "Procure vagas no LinkedIn para Healthcare Assistant em Longford. Se houver Easy Apply, abra o formulário."
        search_url = "https://www.linkedin.com/jobs/search/?keywords=Healthcare"
        job_url = "https://www.linkedin.com/jobs/view/12345/"
        history = [
            {"passo": 1, "ferramenta": "browser_new_tab", "ok": True,
             "args": {"url": search_url}, "resultado": {"status": "ok", "tabId": 101}},
            {"passo": 2, "ferramenta": "browser_read_active_tab", "ok": True,
             "args": {"tab_id": 101},
             "resultado": {"status": "ok", "url": search_url,
                           "links": [{"href": job_url, "text": "Healthcare Assistant"}]}},
            {"passo": 3, "ferramenta": "browser_new_tab", "ok": True,
             "args": {"url": job_url}, "resultado": {"status": "ok", "tabId": 102}},
        ]
        result = simple_task._decidir_proximo_passo(objective, history)
        self.assertEqual(result["ferramenta"], "browser_read_active_tab")
        self.assertEqual(result["args"], {"tab_id": 102})

    def test_easy_apply_click_requires_visible_button_on_job_detail(self):
        objective = "Procure vagas no LinkedIn para Healthcare Assistant em Longford. Se houver Easy Apply, abra o formulário."
        search_url = "https://www.linkedin.com/jobs/search/?keywords=Healthcare"
        job_url = "https://www.linkedin.com/jobs/view/12345/"
        history = [
            {"passo": 1, "ferramenta": "browser_new_tab", "ok": True,
             "args": {"url": search_url}, "resultado": {"status": "ok", "tabId": 101}},
            {"passo": 2, "ferramenta": "browser_read_active_tab", "ok": True,
             "args": {"tab_id": 101},
             "resultado": {"status": "ok", "url": search_url,
                           "links": [{"href": job_url, "text": "Healthcare Assistant"}]}},
            {"passo": 3, "ferramenta": "browser_new_tab", "ok": True,
             "args": {"url": job_url}, "resultado": {"status": "ok", "tabId": 102}},
            {"passo": 4, "ferramenta": "browser_read_active_tab", "ok": True,
             "args": {"tab_id": 102},
             "resultado": {"status": "ok", "url": job_url, "buttons": ["Easy Apply"],
                           "text": "Part-time Healthcare Assistant"}},
        ]
        result = simple_task._decidir_proximo_passo(objective, history)
        self.assertEqual(result["ferramenta"], "browser_click_text")
        self.assertEqual(result["args"], {"text": "Easy Apply", "tab_id": 102})

if __name__ == "__main__":
    unittest.main()
