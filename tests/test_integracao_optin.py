# -*- coding: utf-8 -*-
"""Camada 3 — testes de INTEGRACAO reais (opt-in, desligados por omissao).

Estes testes so correm com MYRA_TEST_INTEGRATION=1 e apenas verificam servicos
JA EM EXECUCAO, sem efeitos destrutivos:

    $env:MYRA_TEST_INTEGRATION = "1"
    venv\\Scripts\\python.exe -m unittest tests.test_integracao_optin -v

Todos os testes sao de LEITURA: nenhum escreve ficheiros, envia email, clica no
PC ou abre abas. Cada teste falha com mensagem clara se o servico nao responder,
para servir de diagnostico rapido do ambiente.
"""
import json
import os
import unittest
import urllib.error
import urllib.request

INTEGRACAO = os.environ.get("MYRA_TEST_INTEGRATION", "").strip() == "1"
MOTIVO = "teste de integracao desligado (define MYRA_TEST_INTEGRATION=1)"

OLLAMA = os.environ.get("OLLAMA_URL_BASE", "http://127.0.0.1:11434")
BACKEND = os.environ.get("MYRA_BACKEND_URL", "http://127.0.0.1:8000")
VISAO = os.environ.get("MYRA_VISAO_URL", "http://127.0.0.1:8081")


def _get(url: str, timeout: int = 5) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _post_json(url: str, payload: dict, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


@unittest.skipUnless(INTEGRACAO, MOTIVO)
class ServicosTestCase(unittest.TestCase):
    """Confirma que os servicos base estao vivos antes de testar o agente."""

    def test_ollama_responde_e_tem_modelo_do_planner(self):
        status, corpo = _get(f"{OLLAMA}/api/tags")
        self.assertEqual(status, 200, f"Ollama nao respondeu em {OLLAMA}")
        nomes = [m.get("name", "") for m in json.loads(corpo).get("models", [])]
        self.assertTrue(nomes, "Ollama sem modelos instalados")
        modelo_planner = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self.assertTrue(
            any(modelo_planner.split(":")[0] in n for n in nomes),
            f"modelo do planner ({modelo_planner}) nao encontrado: {nomes}",
        )

    def test_backend_responde_e_task_status_tem_esquema(self):
        status, corpo = _get(f"{BACKEND}/task_status")
        self.assertEqual(status, 200, f"backend nao respondeu em {BACKEND}")
        dados = json.loads(corpo)
        for chave in ("state", "task_id", "objetivo", "passo_atual", "historico"):
            self.assertIn(chave, dados, f"/task_status sem a chave {chave}")

    def test_servico_de_visao_responde(self):
        status, _ = _get(f"{VISAO}/v1/models")
        self.assertEqual(status, 200, f"servico de visao nao respondeu em {VISAO}")


@unittest.skipUnless(INTEGRACAO, MOTIVO)
class FerramentasReaisTestCase(unittest.TestCase):
    """Exercita o caminho real ferramenta -> backend (SELF HTTP) sem escritas."""

    def test_get_current_time_real(self):
        from tasks import system_tools

        resultado = system_tools.get_current_time()
        self.assertEqual(resultado.get("status"), "ok", f"falhou: {resultado}")
        self.assertTrue(str(resultado.get("result", "")).strip(), "resultado vazio")

    def test_read_notes_real(self):
        from tasks import system_tools

        resultado = system_tools.read_notes()
        self.assertIn(resultado.get("status"), ("ok", "erro"))
        if resultado.get("status") == "erro":
            self.assertIn("result", resultado)

    def test_list_dir_workspace_real_sem_escrita(self):
        from tasks import system_tools

        resultado = system_tools.list_dir(".")
        self.assertEqual(resultado.get("status"), "ok", f"falhou: {resultado}")

    def test_bridge_recusa_sem_token(self):
        status, _ = _get(f"{BACKEND}/browser_bridge/next?wait=0")
        self.assertIn(status, (401, 403, 503), "bridge aceitou pedido sem token valido")

    def test_bridge_aceita_token_do_ambiente(self):
        token = os.environ.get("MYRA_BROWSER_BRIDGE_TOKEN", "").strip()
        if not token:
            self.skipTest("MYRA_BROWSER_BRIDGE_TOKEN nao definido no ambiente")
        req = urllib.request.Request(
            f"{BACKEND}/browser_bridge/next?wait=0",
            headers={"X-MYRA-BRIDGE-TOKEN": token},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        self.assertEqual(status, 200, f"bridge rejeitou o token do ambiente (HTTP {status})")

    def test_vision_locate_real_nao_clica(self):
        """vision_locate real: so localiza, nunca clica. Pode nao encontrar nada."""
        from computer import vision_locate as vl

        resultado = vl.vision_locate("barra de tarefas do Windows")
        self.assertIsInstance(resultado, dict)
        self.assertIn(resultado.get("status"), ("ok", "erro"))
        if resultado.get("status") == "ok" and resultado.get("encontrado"):
            self.assertIn("x", resultado)
            self.assertIn("y", resultado)


if __name__ == "__main__":
    unittest.main()
