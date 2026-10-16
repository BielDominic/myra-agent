# -*- coding: utf-8 -*-
"""Testes severos de contenção de caminhos no workspace (agent.py).

Cobre o bug real encontrado em 2026-10-15: o guard usava
``abspath(destino).startswith(abspath(WORKSPACE_DIR))``, que aceitava prefixos
irmãos — ``../workspace_evil/x`` passava a verificação e permitia ler, escrever,
mover e APAGAR ficheiros fora do workspace. A correção usa
``agent.caminho_no_workspace`` (os.path.commonpath).

Todos os testes correm num WORKSPACE_DIR temporário e sem rede.
"""
import os
import tempfile
import unittest
from pathlib import Path

from tests import helpers


class PathGuardUnitTestCase(unittest.TestCase):
    """Testes unitários directos do helper de contenção."""

    @classmethod
    def setUpClass(cls):
        cls.agent = helpers.importar_agent()

    def setUp(self):
        self._ctx = helpers.workspace_temporario(self.agent)
        self.ws = self._ctx.__enter__()
        self.addCleanup(lambda: self._ctx.__exit__(None, None, None))

    def test_caminho_dentro_do_workspace(self):
        destino = self.agent.caminho_no_workspace("sub/a.txt")
        self.assertTrue(destino.startswith(str(self.ws)))
        self.assertTrue(destino.endswith(os.path.join("sub", "a.txt")))

    def test_caminho_vazio_resolve_para_raiz(self):
        self.assertEqual(self.agent.caminho_no_workspace(""), str(self.ws))

    def test_traversal_simples_rejeitado(self):
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace(os.path.join("..", "fora.txt"))

    def test_prefixo_irmao_rejeitado_regressao(self):
        """Regressão: 'workspace_evil' começa com 'workspace' e passava no guard antigo."""
        irmao = self.ws.parent / f"{self.ws.name}_evil"
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace(f"../{irmao.name}/pwn.txt")

    def test_symlink_para_fora_do_workspace_rejeitado(self):
        externo = self.ws.parent / f"{self.ws.name}_externo"
        externo.mkdir()
        link = self.ws / "atalho_externo"
        try:
            link.symlink_to(externo, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink indisponivel neste ambiente: {exc}")
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace("atalho_externo/segredo.txt")

    def test_caminho_absoluto_rejeitado(self):
        alvo = Path(tempfile.gettempdir()) / "myra_pwn_abs.txt"
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace(str(alvo))

    def test_base_diferente_e_respeitada(self):
        base = self.ws / "code"
        base.mkdir(parents=True, exist_ok=True)
        ok = self.agent.caminho_no_workspace("x.py", str(base))
        self.assertTrue(ok.startswith(str(base)))
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace("../fora.py", str(base))

    def test_travessia_profunda_rejeitada(self):
        with self.assertRaises(ValueError):
            self.agent.caminho_no_workspace("a/b/../../../../etc/passwd")


class RotasFicheirosTestCase(unittest.TestCase):
    """Severidade nas rotas de ficheiros: nada pode sair do workspace."""

    @classmethod
    def setUpClass(cls):
        cls.agent = helpers.importar_agent()
        cls.client = helpers.cliente_agent()

    def setUp(self):
        self._ctx = helpers.workspace_temporario(self.agent)
        self.ws = self._ctx.__enter__()
        self.addCleanup(lambda: self._ctx.__exit__(None, None, None))

    def _post(self, rota, payload):
        return self.client.post(rota, json=payload)

    # ------------------------------------------------------------
    # Comportamento normal (para garantir que a correção não bloqueia o uso legítimo)
    # ------------------------------------------------------------
    def test_ciclo_normal_escrever_ler_listar_apagar(self):
        conteudo = "linha 1\nção ção 😀\n"
        r = self._post("/write_file", {"caminho": "sub/arquivo.txt", "conteudo": conteudo})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertTrue((self.ws / "sub" / "arquivo.txt").is_file())

        r = self._post("/read_file", {"caminho": "sub/arquivo.txt"})
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("ção ção 😀", r.json()["result"])

        r = self._post("/list_dir", {"caminho": "sub"})
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("arquivo.txt", r.json()["result"])

        r = self._post("/delete_file", {"caminho": "sub/arquivo.txt"})
        self.assertEqual(r.json()["status"], "ok")
        self.assertFalse((self.ws / "sub" / "arquivo.txt").exists())

    def test_unicode_no_nome_do_arquivo(self):
        r = self._post("/write_file", {"caminho": "sub/arquivo-ção-😀.txt", "conteudo": "x"})
        self.assertEqual(r.json()["status"], "ok")
        self.assertTrue((self.ws / "sub" / "arquivo-ção-😀.txt").is_file())

    # ------------------------------------------------------------
    # Escapes: todas as rotas devem responder erro e NAO tocar no exterior
    # ------------------------------------------------------------
    def test_write_fora_do_workspace_rejeitado(self):
        vizinho = self.ws.parent / "myra_escape_write"
        if vizinho.exists():
            vizinho.unlink()
        r = self._post("/write_file", {"caminho": "../myra_escape_write", "conteudo": "pwn"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")
        self.assertFalse(vizinho.exists(), "escreveu fora do workspace")

    def test_write_prefixo_irmao_rejeitado_regressao(self):
        irmao = self.ws.parent / f"{self.ws.name}_evil"
        caminho_relativo = f"../{irmao.name}/pwn.txt"
        r = self._post("/write_file", {"caminho": caminho_relativo, "conteudo": "pwn"})
        self.assertEqual(r.json()["status"], "erro")
        self.assertFalse(irmao.exists(), "explorou prefixo irmao do workspace")

    def test_read_absoluto_rejeitado(self):
        alvo = Path(tempfile.gettempdir()) / "myra_segredo_leitura.txt"
        alvo.write_text("segredo-do-sistema", encoding="utf-8")
        self.addCleanup(lambda: alvo.unlink(missing_ok=True))
        r = self._post("/read_file", {"caminho": str(alvo)})
        self.assertEqual(r.json()["status"], "erro")
        self.assertNotIn("segredo-do-sistema", r.json().get("result", ""))

    def test_delete_fora_do_workspace_rejeitado(self):
        alvo = self.ws.parent / "myra_nao_apagar.txt"
        alvo.write_text("manter", encoding="utf-8")
        self.addCleanup(lambda: alvo.unlink(missing_ok=True))
        r = self._post("/delete_file", {"caminho": f"../{alvo.name}"})
        self.assertEqual(r.json()["status"], "erro")
        self.assertTrue(alvo.exists(), "apagou ficheiro fora do workspace")

    def test_create_dir_fora_rejeitado(self):
        alvo = self.ws.parent / "myra_dir_escape"
        r = self._post("/create_dir", {"caminho": f"../{alvo.name}"})
        self.assertEqual(r.json()["status"], "erro")
        self.assertFalse(alvo.exists())

    def test_move_file_fora_rejeitado(self):
        dentro = self.ws / "dentro.txt"
        dentro.write_text("x", encoding="utf-8")
        alvo = self.ws.parent / "myra_move_escape.txt"
        self.addCleanup(lambda: alvo.unlink(missing_ok=True))

        r = self._post("/move_file", {"origem": "dentro.txt", "destino": f"../{alvo.name}"})
        self.assertEqual(r.json()["status"], "erro")
        self.assertTrue(dentro.exists(), "moveu para fora do workspace")
        self.assertFalse(alvo.exists())

        r = self._post("/move_file", {"origem": f"../{alvo.name}", "destino": "roubado.txt"})
        self.assertEqual(r.json()["status"], "erro")
        self.assertFalse((self.ws / "roubado.txt").exists())

    def test_list_dir_fora_rejeitado(self):
        r = self._post("/list_dir", {"caminho": ".."})
        self.assertEqual(r.json()["status"], "erro")

    def test_travessia_profunda_rejeitada_em_todas_as_rotas(self):
        caminho = "a/b/../../../../../../Windows/System32/drivers/etc/hosts"
        for rota, payload in (
            ("/write_file", {"caminho": caminho, "conteudo": "x"}),
            ("/read_file", {"caminho": caminho}),
            ("/delete_file", {"caminho": caminho}),
            ("/create_dir", {"caminho": caminho}),
        ):
            with self.subTest(rota=rota):
                r = self._post(rota, payload)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "erro", f"{rota} aceitou {caminho}")

    def test_code_run_file_fora_rejeitado(self):
        r = self._post("/code_run_file", {"caminho": "../evil.py", "args": [], "timeout": 5})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")

    # ------------------------------------------------------------
    # Entradas degeneradas: nunca 500
    # ------------------------------------------------------------
    def test_entradas_degeneradas_nao_derrubam_o_backend(self):
        casos = [
            ("/write_file", {"caminho": "", "conteudo": "x"}),
            ("/write_file", {"caminho": "a\x00b.txt", "conteudo": "x"}),
            ("/write_file", {"caminho": "sub/", "conteudo": "x"}),
            ("/write_file", {"caminho": "a.txt"}),            # falta conteudo -> 422
            ("/read_file", {"caminho": "\x00"}),
            ("/read_file", {}),                                # falta caminho -> 422
            ("/delete_file", {"caminho": "."}),
            ("/list_dir", {"caminho": "nao_existe_mesmo"}),
            ("/create_dir", {"caminho": ""}),
        ]
        for rota, payload in casos:
            with self.subTest(rota=rota, payload=payload):
                r = self._post(rota, payload)
                self.assertIn(r.status_code, (200, 422))
                if r.status_code == 200:
                    self.assertIn(r.json().get("status"), ("ok", "erro"))

    def test_caminho_muito_longo_nao_derruba(self):
        r = self._post("/write_file", {"caminho": "a" * 5000 + ".txt", "conteudo": "x"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.json()["status"], ("ok", "erro"))


if __name__ == "__main__":
    unittest.main()
