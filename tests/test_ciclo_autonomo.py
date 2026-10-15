# -*- coding: utf-8 -*-
"""Teste end-to-end do ciclo autonomo (FASE 26).

Cobre: observar -> verificar -> concluir com evidencia, recuperar de falhas
com motivo explicito, pausa/continuacao sem perder contexto e retomada apos
crash. Nenhum teste chama LLM, rede ou ferramentas reais: as dependencias
externas sao substituidas por funcoes deterministas.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tasks import autonomy, simple_task, task_store


class FakePlanner:
    """Planner falso: devolve decisoes pre-programadas, repetindo a ultima."""

    def __init__(self, decisoes):
        self.decisoes = list(decisoes)
        self.chamadas = []

    def __call__(self, objetivo, historico, diretriz_recuperacao="", acoes_bloqueadas=None):
        self.chamadas.append({
            "historico_len": len(historico),
            "diretriz": diretriz_recuperacao,
            "bloqueadas": list(acoes_bloqueadas or []),
        })
        if len(self.decisoes) > 1:
            return self.decisoes.pop(0)
        return self.decisoes[0] if self.decisoes else {"acao": "finalizar", "motivo": "fim"}


class CicloAutonomoTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="myra_ciclo_"))
        os.environ["MYRA_TASK_DB"] = str(self.tmp / "tasks.sqlite3")

        # Isola o registro de ferramentas do planner.
        self._ferramentas = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
        self._descricoes = dict(simple_task.FERRAMENTAS_DESCRICOES)
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()

        # Nao dorme entre tentativas e nao chama o LLM de sintese.
        self._patch_sleep = mock.patch("tasks.simple_task.time.sleep", lambda *_: None)
        self._patch_sleep.start()
        self._patch_sintese = mock.patch(
            "tasks.simple_task._sintetizar", lambda objetivo, historico: "sintese final"
        )
        self._patch_sintese.start()

        # Estado global limpo.
        from tasks import cancel_state
        cancel_state.resetar()
        cancel_state.resetar_pausa()

    def tearDown(self):
        mock.patch.stopall()
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(self._ferramentas)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(self._descricoes)
        os.environ.pop("MYRA_TASK_DB", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------
    def _registrar(self, nome, fn):
        simple_task.FERRAMENTAS_DISPONIVEIS[nome] = fn
        simple_task.FERRAMENTAS_DESCRICOES[nome] = "ferramenta de teste"

    # ------------------------------------------------------------
    def test_observa_verifica_e_conclui_com_evidencia(self):
        chamadas = []

        def fake_vision_click(descricao="alvo"):
            chamadas.append(descricao)
            return {"status": "ok", "result": f"cliquei em {descricao}"}

        self._registrar("vision_click", fake_vision_click)
        planner = FakePlanner([
            {"acao": "chamar", "ferramenta": "vision_click", "args": {"descricao": "Entrar"},
             "motivo": "clicar no botao"},
            {"acao": "finalizar", "motivo": "deve nem chegar aqui"},
        ])
        observacao = {
            "status": "ok", "sucesso": True, "objetivo_atingido": True,
            "motivo": "botao Entrar clicado e tela mudou", "proximo_passo_sugerido": "",
        }

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: observacao):
            resultado = simple_task.executar_task("clicar em Entrar", max_passos=5)

        self.assertEqual(resultado["status"], "ok")
        self.assertIn("objetivo verificado", resultado["motivo_encerramento"])
        # O ciclo encerrou pela verificacao, sem esperar o planner finalizar.
        self.assertEqual(len(resultado["historico"]), 1)
        self.assertEqual(len(planner.chamadas), 1)
        self.assertEqual(chamadas, ["Entrar"])
        self.assertEqual(resultado["historico"][0]["observacao"], observacao)
        self.assertTrue(resultado["historico"][0]["verificacao"]["atingido"])

        # Estado persistido como concluido, com historico completo.
        persistida = task_store.carregar_task(resultado["task_id"])
        self.assertEqual(persistida["estado"], task_store.ESTADO_CONCLUIDO)
        self.assertEqual(persistida["resultado_final"], "sintese final")
        self.assertEqual(len(persistida["historico"]), 1)
        self.assertEqual(persistida["historico"][0]["verificacao"]["atingido"], True)
        eventos = [e["tipo"] for e in task_store.listar_eventos(resultado["task_id"])]
        self.assertIn("inicio", eventos)
        self.assertIn("passo", eventos)
        self.assertIn("concluida", eventos)

    def test_falha_gera_recuperacao_e_encerra_com_motivo_explicito(self):
        tentativas = {"n": 0}

        def sempre_falha(descricao="alvo"):
            tentativas["n"] += 1
            return {"status": "erro", "result": f"nao encontrei {descricao}"}

        self._registrar("vision_click", sempre_falha)

        # Cada passo tenta uma acao DIFERENTE (assinatura nova), sempre falhando,
        # ate esgotar o limite de recuperacoes.
        decisoes = [
            {"acao": "chamar", "ferramenta": "vision_click",
             "args": {"descricao": f"alvo {i}"}, "motivo": "tentar clicar"}
            for i in range(6)
        ]
        planner = FakePlanner(decisoes)

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: None):
            resultado = simple_task.executar_task("clicar em algo invisivel", max_passos=10)

        self.assertEqual(resultado["status"], "falhou")
        self.assertIn("limite", resultado["erro"])
        self.assertIn(str(autonomy.LIMITE_RECUPERACOES), resultado["erro"])

        historico = resultado["historico"]
        recuperacoes = [h.get("recuperacao") for h in historico if h.get("recuperacao")]
        # LIMITE_RECUPERACOES tentativas de nova estrategia + a que desiste.
        self.assertEqual(
            len([r for r in recuperacoes if r["recuperar"]]), autonomy.LIMITE_RECUPERACOES
        )
        self.assertTrue(recuperacoes[-1]["desistir"])
        # Cada falha foi registrada com a assinatura bloqueada.
        self.assertTrue(all(r["acoes_bloqueadas"] for r in recuperacoes))

        # O planner recebeu a diretriz de recuperacao no passo seguinte.
        self.assertTrue(planner.chamadas[1]["diretriz"])
        self.assertTrue(planner.chamadas[1]["bloqueadas"])

        persistida = task_store.carregar_task(resultado["task_id"])
        self.assertEqual(persistida["estado"], task_store.ESTADO_FALHOU)
        self.assertIn("limite", persistida["erro"])

    def test_acao_bloqueada_nao_e_reexecutada(self):
        execucoes = {"n": 0}

        def falha(text="Entrar"):
            execucoes["n"] += 1
            return {"status": "erro", "result": "timeout"}

        self._registrar("browser_click_text", falha)
        # Mesma acao sempre (mesma assinatura): a 2a tentativa deve ser recusada
        # pela guarda de recuperacao, sem executar a ferramenta de novo.
        planner = FakePlanner([
            {"acao": "chamar", "ferramenta": "browser_click_text",
             "args": {"text": "Entrar"}, "motivo": "clicar"},
        ])

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: None):
            resultado = simple_task.executar_task("clicar em Entrar", max_passos=6)

        self.assertEqual(resultado["status"], "falhou")
        self.assertIn("bloqueada", resultado["erro"])
        # 2 tentativas internas na 1a execucao; a 2a e 3a vez sao recusadas.
        self.assertEqual(execucoes["n"], 2)
        erros = [h["erro"] for h in resultado["historico"]]
        self.assertIn("acao bloqueada apos falhas repetidas (recuperacao)", erros)

    def test_finalizacao_sem_evidencia_e_recusada(self):
        execucoes = {"n": 0}

        def falha_com_erro(caminho="x.txt", conteudo="a"):
            execucoes["n"] += 1
            return {"status": "erro", "result": "sem permissao"}

        self._registrar("write_file", falha_com_erro)
        # Planner tenta escrever, falha, e pede finalizar (mentindo sucesso).
        planner = FakePlanner([
            {"acao": "chamar", "ferramenta": "write_file",
             "args": {"caminho": "x.txt", "conteudo": "a"}, "motivo": "escrever"},
            {"acao": "finalizar", "motivo": "arquivo criado"},
        ])

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: None):
            resultado = simple_task.executar_task("criar x.txt", max_passos=6)

        # A finalizacao foi recusada e, sem conseguir nova estrategia, encerrou
        # com motivo explicito em vez de declarar sucesso.
        self.assertTrue(any(
            "finalizacao_recusada" == e["tipo"]
            for e in task_store.listar_eventos(resultado["task_id"])
        ) or resultado["status"] == "falhou")
        self.assertNotEqual(resultado["status"], "ok")

    def test_retomada_preserva_acoes_bloqueadas(self):
        execucoes = {"n": 0}

        def falha(descricao="alvo"):
            execucoes["n"] += 1
            return {"status": "erro", "result": "timeout"}

        self._registrar("vision_click", falha)

        # Task retomavel cujo historico registra uma recuperacao que bloqueou
        # a acao vision_click({"descricao": "alvo"}).
        t = task_store.criar_task("clicar no alvo", max_passos=6)
        assinatura = autonomy.assinatura_acao("vision_click", {"descricao": "alvo"})
        task_store.salvar_task(
            t["task_id"],
            passo_atual=1,
            estado=task_store.ESTADO_PAUSADO,
            historico=[{
                "passo": 1,
                "ferramenta": "vision_click",
                "args": {"descricao": "alvo"},
                "ok": False,
                "resultado": None,
                "erro": "timeout",
                "verificacao": {"atingido": False, "confianca": "alta",
                                "motivo": "a ultima acao falhou: timeout", "evidencia": "timeout"},
                "recuperacao": {"recuperar": True, "desistir": False, "tentativas": 1,
                                "motivo": "falha em vision_click: timeout",
                                "diretriz": "use outra estrategia",
                                "acoes_bloqueadas": [assinatura]},
            }],
        )

        planner = FakePlanner([
            {"acao": "chamar", "ferramenta": "vision_click",
             "args": {"descricao": "alvo"}, "motivo": "tentar de novo"},
        ])

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: None):
            resultado = simple_task.retomar_task(t["task_id"])

        # A acao bloqueada nunca e reexecutada apos a retomada.
        self.assertEqual(execucoes["n"], 0)
        self.assertEqual(resultado["status"], "falhou")
        self.assertIn("bloqueada", resultado["erro"])
        self.assertTrue(planner.chamadas[0]["bloqueadas"], "a diretriz deve listar a acao bloqueada")
        # O historico anterior continua no resultado.
        self.assertEqual(resultado["historico"][0]["passo"], 1)

    def test_pausa_e_retomada_preservam_contexto(self):
        contador = {"n": 0}

        def click(descricao="alvo"):
            contador["n"] += 1
            return {"status": "ok", "result": f"cliquei em {descricao}"}

        self._registrar("vision_click", click)

        def planner(objetivo, historico, diretriz_recuperacao="", acoes_bloqueadas=None):
            return {
                "acao": "chamar",
                "ferramenta": "vision_click",
                "args": {"descricao": f"alvo {len(historico) + 1}"},
                "motivo": "proximo clique",
            }

        # Observacao: acao ok, objetivo ainda nao atingido -> o loop continua.
        obs_parcial = {
            "status": "ok", "sucesso": True, "objetivo_atingido": False,
            "motivo": "clique feito, falta o proximo", "proximo_passo_sugerido": "continuar",
        }

        # Pausa depois de 2 verificacoes de estado (fim do passo 1).
        estado_pausa = {"chamadas": 0}
        real_esta_pausada = simple_task.esta_pausada

        def pausa_controlada():
            estado_pausa["chamadas"] += 1
            return estado_pausa["chamadas"] > 2

        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: obs_parcial), \
             mock.patch.object(simple_task, "esta_pausada", pausa_controlada):
            primeira = simple_task.executar_task("clicar em dois botoes", max_passos=5)

        self.assertEqual(primeira["status"], "pausado")
        task_id = primeira["task_id"]
        self.assertTrue(task_id)
        self.assertEqual(len(primeira["historico"]), 1)

        persistida = task_store.carregar_task(task_id)
        self.assertEqual(persistida["estado"], task_store.ESTADO_PAUSADO)
        self.assertEqual(len(persistida["historico"]), 1)
        self.assertEqual(persistida["historico"][0]["observacao"], obs_parcial)
        self.assertIn(task_id, [t["task_id"] for t in simple_task.listar_tasks_pendentes()])

        # Retoma: agora o observer confirma o objetivo no proximo clique.
        obs_final = {
            "status": "ok", "sucesso": True, "objetivo_atingido": True,
            "motivo": "os dois cliques foram feitos", "proximo_passo_sugerido": "",
        }
        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner), \
             mock.patch.object(simple_task, "_observar", lambda *a, **k: obs_final):
            segunda = simple_task.retomar_task(task_id)

        self.assertEqual(segunda["status"], "ok")
        self.assertEqual(segunda["task_id"], task_id)
        # O contexto anterior foi preservado (passo 1 + passo 2).
        self.assertEqual(len(segunda["historico"]), 2)
        self.assertEqual(segunda["historico"][0]["observacao"], obs_parcial)
        self.assertTrue(segunda["historico"][1]["verificacao"]["atingido"])

        final = task_store.carregar_task(task_id)
        self.assertEqual(final["estado"], task_store.ESTADO_CONCLUIDO)
        self.assertEqual(len(final["historico"]), 2)

    def test_retomada_apos_crash(self):
        def leitura():
            return {"status": "ok", "result": "conteudo lido"}

        self._registrar("browser_read_page", leitura)

        # Task deixada por um processo que morreu no meio (run_id antigo).
        antiga = task_store.criar_task("ler a pagina", max_passos=5)
        task_store.salvar_task(
            antiga["task_id"],
            passo_atual=1,
            historico=[{
                "passo": 1,
                "ferramenta": "browser_read_page",
                "args": {"url": "http://exemplo"},
                "ok": True,
                "resultado": {"text": "parcial"},
            }],
        )
        with task_store._lock:
            conn = task_store._connect()
            try:
                conn.execute(
                    "UPDATE tasks SET run_id = 'run-morto' WHERE task_id = ?",
                    (antiga["task_id"],),
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

        planner = FakePlanner([{"acao": "finalizar", "motivo": "ja tenho o conteudo"}])
        with mock.patch.object(simple_task, "_decidir_proximo_passo", planner):
            resultado = simple_task.retomar_task(antiga["task_id"])

        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(resultado["historico"][0]["passo"], 1)
        self.assertEqual(len(planner.chamadas), 1)

        tipos = [e["tipo"] for e in task_store.listar_eventos(antiga["task_id"])]
        self.assertIn("interrompida", tipos)
        self.assertIn("retomada_apos_interrupcao", tipos)

    def test_cancelamento_persiste_estado_cancelado(self):
        self._registrar("vision_click", lambda descricao="alvo": {"status": "ok", "result": "ok"})
        with mock.patch.object(simple_task, "esta_cancelada", lambda: True):
            resultado = simple_task.executar_task("qualquer coisa", max_passos=3)

        self.assertEqual(resultado["status"], "cancelado")
        persistida = task_store.carregar_task(resultado["task_id"])
        self.assertEqual(persistida["estado"], task_store.ESTADO_CANCELADO)

    def test_sem_ferramentas_retorna_erro(self):
        resultado = simple_task.executar_task("nada", max_passos=2)
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("Nenhuma ferramenta", resultado["erro"])

    def test_retomar_task_final_nao_e_permitido(self):
        t = task_store.criar_task("ja feita")
        task_store.salvar_task(t["task_id"], estado=task_store.ESTADO_CONCLUIDO, terminado=True)
        resultado = simple_task.retomar_task(t["task_id"])
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("nao pode ser retomada", resultado["erro"])

    def test_retomar_task_inexistente(self):
        resultado = simple_task.retomar_task("task-fantasma")
        self.assertEqual(resultado["status"], "erro")
        self.assertIn("nao encontrada", resultado["erro"])


if __name__ == "__main__":
    unittest.main()
