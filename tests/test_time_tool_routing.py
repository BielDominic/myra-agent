"""Regressoes da selecao de ferramenta para pedidos de hora atual."""
import unittest
from unittest.mock import patch

import tasks.simple_task as simple_task


class TestTimeToolRouting(unittest.TestCase):
    def setUp(self):
        self._ferramentas = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        self._descricoes = dict(simple_task.FERRAMENTAS_DESCRICOES)
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.registrar_ferramenta(
            "get_current_time",
            lambda: {"status": "ok", "result": "16/10/2026 19:15:00 (sexta)"},
            "hora/data atual",
        )

    def tearDown(self):
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self._ferramentas)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(self._descricoes)

    def test_pedido_hora_nao_pode_ser_finalizado_sem_ferramenta(self):
        with patch.object(
            simple_task,
            "_llm",
            return_value='{"acao":"finalizar","motivo":"nao sei"}',
        ):
            decisao = simple_task._decidir_proximo_passo("que horas sao", [])

        self.assertEqual(decisao["acao"], "chamar")
        self.assertEqual(decisao["ferramenta"], "get_current_time")
        self.assertEqual(decisao["args"], {})

    def test_pedido_hora_recupera_json_invalido_do_planner(self):
        with patch.object(simple_task, "_llm", return_value="Nao sei responder"):
            decisao = simple_task._decidir_proximo_passo("Que horas são?", [])

        self.assertEqual(decisao["acao"], "chamar")
        self.assertEqual(decisao["ferramenta"], "get_current_time")

    def test_pedido_hora_preserva_decisao_correta_do_modelo(self):
        resposta = (
            '{"acao":"chamar","ferramenta":"get_current_time",'
            '"args":{},"motivo":"consultar a hora"}'
        )
        with patch.object(simple_task, "_llm", return_value=resposta):
            decisao = simple_task._decidir_proximo_passo("que horas sao", [])

        self.assertEqual(decisao["acao"], "chamar")
        self.assertEqual(decisao["ferramenta"], "get_current_time")

    def test_executar_task_realmente_executa_ferramenta_de_hora(self):
        with (
            patch.object(
                simple_task,
                "_llm",
                return_value='{"acao":"finalizar","motivo":"concluido"}',
            ),
            patch.object(
                simple_task.autonomy,
                "verificar",
                return_value={
                    "atingido": True,
                    "confianca": "alta",
                    "motivo": "a ferramenta retornou a hora atual",
                },
            ),
            patch.object(simple_task, "_sintetizar", return_value="19:15:00"),
        ):
            resultado = simple_task.executar_task(
                "que horas sao",
                max_passos=3,
                persistir=False,
            )

        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(len(resultado["historico"]), 1)
        self.assertEqual(resultado["historico"][0]["ferramenta"], "get_current_time")
        self.assertTrue(resultado["historico"][0]["ok"])
        self.assertEqual(resultado["resultado_final"], "19:15:00")

    def test_nao_interfere_com_pedido_sem_relacao_com_hora(self):
        with patch.object(
            simple_task,
            "_llm",
            return_value='{"acao":"finalizar","motivo":"concluido"}',
        ):
            decisao = simple_task._decidir_proximo_passo("ola", [])

        self.assertEqual(decisao["acao"], "finalizar")


if __name__ == "__main__":
    unittest.main()
