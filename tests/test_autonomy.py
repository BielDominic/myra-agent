# -*- coding: utf-8 -*-
"""Testes da verificacao de objetivo e da recuperacao de falhas (FASE 26)."""
import unittest

from tasks import autonomy


def passo(passo_num, ferramenta, args, ok, erro=None, observacao=None, resultado=None):
    return {
        "passo": passo_num,
        "ferramenta": ferramenta,
        "args": args,
        "ok": ok,
        "erro": erro,
        "resultado": resultado,
        "observacao": observacao,
    }


class VerificarTestCase(unittest.TestCase):
    def test_historico_vazio_e_indeterminado(self):
        v = autonomy.verificar("abrir o github", [])
        self.assertIsNone(v["atingido"])
        self.assertEqual(v["confianca"], "indeterminada")

    def test_observer_confirma_objetivo(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "aba aberta"}
        v = autonomy.verificar("abrir o github", [passo(1, "browser_new_tab", {}, True, observacao=obs)], obs)
        self.assertTrue(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("aba aberta", v["motivo"])

    def test_navegacao_nao_satisfaz_objetivo_que_exige_leitura_de_pagina(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "pagina aberta"}
        resultado = {"status": "ok", "url": "https://example.com/", "title": "Example Domain"}
        historico = [passo(1, "browser_new_tab", {"url": "https://example.com"}, True,
                           observacao=obs, resultado=resultado)]
        v = autonomy.verificar(
            "Abra https://example.com, leia o conteudo principal da pagina e informe o primeiro paragrafo.",
            historico,
            obs,
        )
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("browser_read_page", v["motivo"])

    def test_navegacao_pode_satisfazer_objetivo_simples_de_abrir_pagina(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "pagina aberta"}
        historico = [passo(1, "browser_new_tab", {"url": "https://example.com"}, True,
                           observacao=obs, resultado={"status": "ok", "url": "https://example.com/", "title": "Example Domain"})]
        v = autonomy.verificar("abra example.com", historico, obs)
        self.assertTrue(v["atingido"])

    def test_navegacao_nao_satisfaz_objetivo_que_exige_clique(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "pagina aberta"}
        resultado = {"status": "ok", "url": "https://example.com/", "title": "Example Domain"}
        historico = [passo(1, "browser_new_tab", {"url": "https://example.com"}, True,
                           observacao=obs, resultado=resultado)]
        v = autonomy.verificar("Abra example.com e clique no link Learn more", historico, obs)
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("interacao solicitada", v["motivo"])

    def test_leitura_nao_satisfaz_objetivo_que_exige_clique(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "pagina lida"}
        resultado = {"status": "ok", "url": "https://example.com/", "title": "Example Domain",
                     "text": "Learn more"}
        historico = [passo(1, "browser_read_active_tab", {}, True, observacao=obs, resultado=resultado)]
        v = autonomy.verificar("Abra example.com e clique no link Learn more", historico, obs)
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("interacao solicitada", v["motivo"])

    def test_leitura_de_pagina_satisfaz_objetivo_de_extracao(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "titulo e paragrafo extraidos"}
        resultado = {"status": "ok", "url": "https://example.com/", "title": "Example Domain",
                     "text": "This domain is for use in documentation examples."}
        historico = [passo(1, "browser_read_page", {}, True, observacao=obs, resultado=resultado)]
        v = autonomy.verificar("leia o conteudo da pagina e informe o primeiro paragrafo", historico, obs)
        self.assertTrue(v["atingido"])

    def test_leitura_sem_texto_nao_satisfaz_objetivo_de_extracao(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "pagina lida"}
        resultado = {"status": "ok", "url": "https://example.com/", "title": "Example Domain", "text": ""}
        historico = [passo(1, "browser_read_active_tab", {}, True, observacao=obs, resultado=resultado)]
        v = autonomy.verificar("leia o conteudo da pagina e informe o primeiro paragrafo", historico, obs)
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("nao retornou texto", v["motivo"])

    def test_observer_confirma_falha_da_acao(self):
        obs = {"status": "ok", "sucesso": False, "objetivo_atingido": False, "motivo": "botao inexistente"}
        v = autonomy.verificar("clicar em entrar", [passo(1, "browser_click_text", {}, True, observacao=obs)], obs)
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")

    def test_observer_diz_que_objetivo_nao_foi_atingido(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": False, "motivo": "faltou confirmar"}
        v = autonomy.verificar("enviar email", [passo(1, "email_send", {}, True, observacao=obs)], obs)
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "media")

    def test_execucao_com_erro_nunca_e_sucesso(self):
        obs = {"status": "ok", "sucesso": True, "objetivo_atingido": True, "motivo": "otimista"}
        v = autonomy.verificar(
            "clicar", [passo(1, "browser_click_text", {}, False, erro="timeout", observacao=obs)], obs
        )
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("timeout", v["motivo"])

    def test_resultado_com_status_erro_nunca_e_sucesso(self):
        v = autonomy.verificar(
            "escrever arquivo",
            [passo(1, "write_file", {}, True, resultado={"status": "erro", "result": "sem permissao"})],
        )
        self.assertFalse(v["atingido"])
        self.assertEqual(v["confianca"], "alta")
        self.assertIn("sem permissao", v["motivo"])

    def test_sem_observacao_nao_declara_sucesso(self):
        v = autonomy.verificar("ler a pagina", [passo(1, "browser_read_page", {}, True)])
        self.assertIsNone(v["atingido"])
        self.assertEqual(v["confianca"], "indeterminada")

    def test_observer_indisponivel_nao_declara_sucesso(self):
        obs = {"status": "erro", "result": "erro ao chamar LLM"}
        v = autonomy.verificar("ler", [passo(1, "browser_read_page", {}, True, observacao=obs)], obs)
        self.assertIsNone(v["atingido"])


class RecuperarTestCase(unittest.TestCase):
    def test_primeira_falha_pede_nova_estrategia(self):
        historico = [passo(1, "browser_click_text", {"text": "Entrar"}, False, erro="timeout")]
        r = autonomy.recuperar("browser_click_text", {"text": "Entrar"}, "timeout", historico)
        self.assertTrue(r["recuperar"])
        self.assertFalse(r["desistir"])
        self.assertIn("vision_click", r["diretriz"])
        self.assertEqual(len(r["acoes_bloqueadas"]), 1)

    def test_segunda_falha_da_mesma_acao_desiste(self):
        historico = [
            passo(1, "browser_click_text", {"text": "Entrar"}, False, erro="timeout"),
            passo(2, "browser_click_text", {"text": "Entrar"}, False, erro="timeout"),
        ]
        r = autonomy.recuperar("browser_click_text", {"text": "Entrar"}, "timeout", historico)
        self.assertFalse(r["recuperar"])
        self.assertTrue(r["desistir"])
        self.assertIn("bloqueada", r["motivo"])
        self.assertEqual(r["tentativas"], 2)

    def test_limite_de_recuperacoes_encerra_com_motivo(self):
        historico = [passo(1, "browser_type_text", {"campo": "#a", "texto": "x"}, False, erro="seletor invalido")]
        r = autonomy.recuperar(
            "browser_type_text", {"campo": "#a", "texto": "x"}, "seletor invalido",
            historico, recuperacoes_usadas=autonomy.LIMITE_RECUPERACOES,
        )
        self.assertTrue(r["desistir"])
        self.assertIn("limite", r["motivo"])

    def test_assinatura_estavel_independente_da_ordem_das_chaves(self):
        a = autonomy.assinatura_acao("f", {"a": 1, "b": 2})
        b = autonomy.assinatura_acao("f", {"b": 2, "a": 1})
        self.assertEqual(a, b)

    def test_contar_falhas_ignora_sucessos(self):
        assinatura = autonomy.assinatura_acao("f", {"x": 1})
        historico = [
            passo(1, "f", {"x": 1}, True),
            passo(2, "f", {"x": 1}, False),
            passo(3, "f", {"x": 1}, False),
            passo(4, "outra", {}, False),
        ]
        self.assertEqual(autonomy.contar_falhas(historico, assinatura), 2)

    def test_sugestao_padrao_para_ferramenta_desconhecida(self):
        historico = [passo(1, "ferramenta_nova", {"a": 1}, False, erro="boom")]
        r = autonomy.recuperar("ferramenta_nova", {"a": 1}, "boom", historico)
        self.assertIn(autonomy.SUGESTAO_PADRAO, r["diretriz"])

    def test_resumo_recuperacoes(self):
        historico = [{
            "passo": 1,
            "recuperacao": {"desistir": False, "motivo": "tentando de novo"},
        }]
        resumo = autonomy.resumo_recuperacoes(historico)
        self.assertIn("passo 1", resumo)
        self.assertIn("nova tentativa", resumo)


if __name__ == "__main__":
    unittest.main()
