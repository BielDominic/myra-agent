# -*- coding: utf-8 -*-
"""Testes da persistencia de tasks (FASE 26).

Executar da raiz do repo:
    python -m unittest discover -s tests -t .
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tasks import task_store


class TaskStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="myra_store_"))
        os.environ["MYRA_TASK_DB"] = str(self.tmp / "tasks.sqlite3")

    def tearDown(self):
        os.environ.pop("MYRA_TASK_DB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------
    def test_criar_e_carregar_task(self):
        t = task_store.criar_task("abrir o github", max_passos=7)
        self.assertEqual(t["estado"], task_store.ESTADO_EM_EXECUCAO)
        self.assertEqual(t["objetivo"], "abrir o github")
        self.assertEqual(t["max_passos"], 7)
        self.assertEqual(t["historico"], [])

        carregada = task_store.carregar_task(t["task_id"])
        self.assertIsNotNone(carregada)
        self.assertEqual(carregada["task_id"], t["task_id"])

    def test_objetivo_vazio_e_rejeitado(self):
        with self.assertRaises(ValueError):
            task_store.criar_task("   ")

    def test_salvar_historico_com_acentos_e_objetos(self):
        t = task_store.criar_task("pesquisar noticias")
        historico = [{
            "passo": 1,
            "ferramenta": "browser_search_google",
            "args": {"termo": "eleições"},
            "ok": True,
            "resultado": {"text": "notícia ção"},
            "observacao": {"status": "ok", "sucesso": True, "objetivo_atingido": False},
        }]
        task_store.salvar_task(t["task_id"], passo_atual=1, historico=historico)

        carregada = task_store.carregar_task(t["task_id"])
        self.assertEqual(carregada["passo_atual"], 1)
        self.assertEqual(carregada["historico"][0]["args"]["termo"], "eleições")
        self.assertEqual(carregada["historico"][0]["resultado"]["text"], "notícia ção")

    def test_salvar_task_inexistente_retorna_none(self):
        self.assertIsNone(task_store.salvar_task("nao-existe", estado="pausado"))

    def test_pausa_e_retomavel(self):
        t = task_store.criar_task("tarefa longa")
        task_store.salvar_task(t["task_id"], estado=task_store.ESTADO_PAUSADO)
        retomaveis = [x["task_id"] for x in task_store.tasks_retomaveis()]
        self.assertIn(t["task_id"], retomaveis)

        task_store.salvar_task(
            t["task_id"], estado=task_store.ESTADO_CONCLUIDO, terminado=True
        )
        retomaveis = [x["task_id"] for x in task_store.tasks_retomaveis()]
        self.assertNotIn(t["task_id"], retomaveis)
        self.assertIsNotNone(task_store.carregar_task(t["task_id"])["terminado_em"])

    def test_listar_tasks_filtra_por_estado(self):
        a = task_store.criar_task("a")
        b = task_store.criar_task("b")
        task_store.salvar_task(b["task_id"], estado=task_store.ESTADO_FALHOU)

        em_execucao = [x["task_id"] for x in task_store.listar_tasks(estado=task_store.ESTADO_EM_EXECUCAO)]
        self.assertIn(a["task_id"], em_execucao)
        self.assertNotIn(b["task_id"], em_execucao)

        # listar_tasks nao carrega historico (resposta leve)
        self.assertNotIn("historico", task_store.listar_tasks()[0])

    def test_marcar_interrompidas_apenas_de_outras_execucoes(self):
        antiga = task_store.criar_task("task antiga")
        atual = task_store.criar_task("task deste processo")

        # Simula uma task de uma execucao anterior (run_id diferente).
        task_store.salvar_task(antiga["task_id"], estado=task_store.ESTADO_EM_EXECUCAO)
        with task_store._lock:
            conn = task_store._connect()
            try:
                conn.execute(
                    "UPDATE tasks SET run_id = ? WHERE task_id = ?",
                    ("run-antigo", antiga["task_id"]),
                )
                conn.commit()
            finally:
                conn.close()

        marcadas = task_store.marcar_interrompidas(run_id=task_store.RUN_ID)
        self.assertEqual(marcadas, 1)
        self.assertEqual(
            task_store.carregar_task(antiga["task_id"])["estado"],
            task_store.ESTADO_INTERROMPIDO,
        )
        self.assertEqual(
            task_store.carregar_task(atual["task_id"])["estado"],
            task_store.ESTADO_EM_EXECUCAO,
        )

    def test_eventos_da_task(self):
        t = task_store.criar_task("com eventos")
        task_store.registrar_evento(t["task_id"], "inicio", "comecou")
        task_store.registrar_evento(t["task_id"], "passo", "get_current_time", passo=1)

        eventos = task_store.listar_eventos(t["task_id"])
        self.assertEqual([e["tipo"] for e in eventos], ["inicio", "passo"])
        self.assertEqual(eventos[1]["passo"], 1)

    def test_apagar_task_remove_eventos(self):
        t = task_store.criar_task("descartavel")
        task_store.registrar_evento(t["task_id"], "inicio")
        self.assertTrue(task_store.apagar_task(t["task_id"]))
        self.assertIsNone(task_store.carregar_task(t["task_id"]))
        self.assertEqual(task_store.listar_eventos(t["task_id"]), [])

    def test_persistencia_sobrevive_a_reabertura(self):
        t = task_store.criar_task("sobreviver")
        task_store.salvar_task(
            t["task_id"],
            estado=task_store.ESTADO_PAUSADO,
            passo_atual=2,
            historico=[{"passo": 1, "ferramenta": "x", "ok": True}],
        )
        # Simula outro processo lendo o mesmo banco.
        task_store._initialized_paths.discard(task_store.db_path())
        carregada = task_store.carregar_task(t["task_id"])
        self.assertEqual(carregada["estado"], task_store.ESTADO_PAUSADO)
        self.assertEqual(carregada["passo_atual"], 2)
        self.assertEqual(len(carregada["historico"]), 1)


if __name__ == "__main__":
    unittest.main()
