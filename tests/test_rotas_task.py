# -*- coding: utf-8 -*-
"""Smoke test das rotas de pausa/retomada do agent.py (FASE 26).

Usa o TestClient do FastAPI, sem LLM e sem rede: valida apenas o contrato HTTP
das rotas novas (/task_pause, /task_pendentes, /task_detalhe) e o estado
persistido. /task_resume nao e exercitado aqui porque depende do planner
(Ollama); esse caminho e coberto por tests/test_ciclo_autonomo.py.
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

os.environ.setdefault("MYRA_TASK_DB", str(Path(tempfile.gettempdir()) / "myra_smoke_tasks.sqlite3"))

try:
    from fastapi.testclient import TestClient
    import agent as agent_module
    from tasks import task_store
    DISPONIVEL = True
except Exception as e:  # pragma: no cover - ambiente sem dependencias do agent
    DISPONIVEL = False
    MOTIVO = str(e)


@unittest.skipUnless(DISPONIVEL, "agent.py indisponivel neste ambiente")
class RotasTaskTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="myra_http_"))
        os.environ["MYRA_TASK_DB"] = str(self.tmp / "tasks.sqlite3")
        from tasks import cancel_state
        cancel_state.resetar()
        cancel_state.resetar_pausa()
        self.client = TestClient(agent_module.app)

    def tearDown(self):
        from tasks import cancel_state
        cancel_state.resetar()
        cancel_state.resetar_pausa()
        os.environ.pop("MYRA_TASK_DB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_browser_wait_nao_tenta_abrir_perfil_persistente(self):
        with mock.patch.object(agent_module.time, "sleep") as dormir, \
             mock.patch.object(agent_module, "start_browser", side_effect=AssertionError("nao deve abrir navegador")) as iniciar:
            resultado = agent_module._t_browser_wait(ms=12000)
        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(resultado["result"], "Esperei 12s")
        dormir.assert_called_once_with(12.0)
        iniciar.assert_not_called()

    def test_browser_wait_limita_intervalo(self):
        with mock.patch.object(agent_module.time, "sleep") as dormir:
            resultado = agent_module._t_browser_wait(ms=999999)
        self.assertEqual(resultado["status"], "ok")
        dormir.assert_called_once_with(30.0)

    def test_task_pause_marca_flag_e_responde_task_id(self):
        agent_module._widget_set(state="running", task_id="task-abc")
        from tasks.cancel_state import esta_pausada

        self.assertFalse(esta_pausada())
        resp = self.client.post("/task_pause")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["task_id"], "task-abc")
        self.assertTrue(esta_pausada())

    def test_task_pendentes_lista_tasks_retomaveis(self):
        t = task_store.criar_task("esperando retomada")
        task_store.salvar_task(t["task_id"], estado=task_store.ESTADO_PAUSADO)

        resp = self.client.get("/task_pendentes")
        self.assertEqual(resp.status_code, 200)
        ids = [x["task_id"] for x in resp.json()["tasks"]]
        self.assertIn(t["task_id"], ids)

    def test_task_detalhe_traz_historico_e_eventos(self):
        t = task_store.criar_task("com detalhe")
        task_store.salvar_task(
            t["task_id"], passo_atual=1,
            historico=[{"passo": 1, "ferramenta": "get_current_time", "ok": True}],
        )
        task_store.registrar_evento(t["task_id"], "passo", "get_current_time", passo=1)

        resp = self.client.get(f"/task_detalhe/{t['task_id']}")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(len(corpo["task"]["historico"]), 1)
        self.assertEqual(corpo["task"]["eventos"][0]["tipo"], "passo")

    def test_task_detalhe_de_task_inexistente(self):
        resp = self.client.get("/task_detalhe/task-que-nao-existe")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "erro")

    def test_task_resume_com_task_inexistente(self):
        resp = self.client.post("/task_resume", json={"task_id": "task-fantasma"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "erro")

    def test_task_resume_recusa_task_concluida(self):
        t = task_store.criar_task("concluida")
        task_store.salvar_task(
            t["task_id"], estado=task_store.ESTADO_CONCLUIDO, terminado=True
        )
        resp = self.client.post("/task_resume", json={"task_id": t["task_id"]})
        self.assertEqual(resp.json()["status"], "erro")
        self.assertIn("nao pode ser retomada", resp.json()["result"])

    def test_task_cancel_limpa_pausa(self):
        from tasks.cancel_state import esta_pausada, esta_cancelada

        self.client.post("/task_pause")
        self.assertTrue(esta_pausada())
        self.client.post("/task_cancel")
        self.assertFalse(esta_pausada())
        self.assertTrue(esta_cancelada())


if __name__ == "__main__":
    unittest.main()
