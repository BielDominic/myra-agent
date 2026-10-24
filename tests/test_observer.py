# -*- coding: utf-8 -*-
"""Testes offline do contrato do observer."""
import json
import unittest
from unittest import mock

from computer import observer


class ObserverTestCase(unittest.TestCase):
    def _resposta(self, texto):
        return mock.patch.object(
            observer.urllib.request,
            "urlopen",
            return_value=_FakeResponse({"message": {"content": texto}}),
        )

    def test_booleanos_json_sao_preservados(self):
        with self._resposta('{"sucesso": true, "objetivo_atingido": false, "motivo": "ainda falta"}'):
            resultado = observer.observar("concluir tarefa", {"ferramenta": "x"})
        self.assertIs(resultado["sucesso"], True)
        self.assertIs(resultado["objetivo_atingido"], False)

    def test_string_false_nunca_vira_true(self):
        with self._resposta('{"sucesso": "false", "objetivo_atingido": "false"}'):
            resultado = observer.observar("concluir tarefa", {"ferramenta": "x"})
        self.assertIs(resultado["sucesso"], False)
        self.assertIs(resultado["objetivo_atingido"], False)

    def test_valor_ambiguo_nao_confirma_sucesso(self):
        with self._resposta('{"sucesso": "talvez", "objetivo_atingido": true}'):
            resultado = observer.observar("concluir tarefa", {"ferramenta": "x"})
        self.assertIsNone(resultado["sucesso"])
        self.assertIsNone(resultado["objetivo_atingido"])

    def test_prompt_tem_quebras_de_linha_reais(self):
        captured = {}
        def urlopen(req, timeout=0):
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse({"message": {"content": '{"sucesso":true,"objetivo_atingido":false}'} })
        with mock.patch.object(observer.urllib.request, "urlopen", urlopen):
            observer.observar("abrir o site", {"ferramenta": "browser_new_tab"})
        prompt = captured["payload"]["messages"][0]["content"]
        self.assertIn("\n", prompt)
        self.assertNotIn("\\n", prompt)

    def test_resumo_preserva_evidencia_ui_aninhada_sem_promover_mudanca_a_sucesso(self):
        resultado = {
            "status": "ok",
            "verified": False,
            "result": {
                "mudanca_observavel": True,
                "evidencia_antes": {"value": "antes"},
                "evidencia_depois": {"value": "depois"},
            },
        }
        resumo = json.loads(observer._resumir_evidencia_ui(resultado))
        self.assertTrue(resumo["mudanca_observavel"])
        self.assertFalse(resumo["verified"])
        self.assertEqual(resumo["evidencia_antes"]["value"], "antes")
        self.assertEqual(resumo["evidencia_depois"]["value"], "depois")

    def test_prompt_expoe_evidencia_uia_depois_de_resultado_longo(self):
        captured = {}
        def urlopen(req, timeout=0):
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse({"message": {"content": '{"sucesso":true,"objetivo_atingido":false}'} })
        acao = {
            "ferramenta": "pc_control_action",
            "resultado": {
                "status": "ok", "result": {"texto_longo": "x" * 1200,
                    "mudanca_observavel": True,
                    "evidencia_antes": {"value": "antes"},
                    "evidencia_depois": {"value": "depois"}},
            },
        }
        with mock.patch.object(observer.urllib.request, "urlopen", urlopen):
            observer.observar("instalar aplicativo", acao)
        prompt = captured["payload"]["messages"][0]["content"]
        self.assertIn("EVIDENCIA ESTRUTURADA UIA", prompt)
        self.assertIn('"mudanca_observavel": true', prompt)
        self.assertIn('"value": "depois"', prompt)
        self.assertIn("mudanca nao significa objetivo concluido", prompt)

    def test_resposta_invalida_e_indeterminada(self):
        with self._resposta("não é JSON"):
            resultado = observer.observar("concluir tarefa", {"ferramenta": "x"})
        self.assertIsNone(resultado["sucesso"])
        self.assertIsNone(resultado["objetivo_atingido"])

    def test_objetivo_vazio_nao_chama_llm(self):
        with mock.patch.object(observer.urllib.request, "urlopen") as chamada:
            resultado = observer.observar("  ")
        self.assertEqual(resultado["status"], "erro")
        chamada.assert_not_called()


class _FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.body


if __name__ == "__main__":
    unittest.main()
