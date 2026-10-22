# -*- coding: utf-8 -*-
"""Testes severos de contrato das rotas HTTP NAO destrutivas do agent.py.

Alvo (via ``helpers.cliente_agent()``, sem abrir portas reais):

    GET  /                       GET  /v1/models
    GET  /task_status            GET  /task_pendentes
    GET  /task_detalhe/{id}
    POST /get_current_time       POST /save_note      POST /read_notes
    POST /code_metrics           POST /code_lint
    POST /code_diff              POST /code_regex     POST /code_sql
    POST /code_scaffold

Regras de seguranca aplicadas em TODOS os testes (classe ``BaseRotas``):

* ``helpers.AmbienteIsolado`` (bancos em tmp) + ``helpers.workspace_temporario``;
* ``agent.NOTES_FILE`` apontado para tmp (o ficheiro real do repo nunca e escrito);
* ``GMAIL_USER`` / ``GMAIL_APP_PASSWORD`` / ``OPENWEBUI_API_KEY`` limpos (env e
  constantes do modulo) para que as rotas de email/chat caiam no caminho de erro;
* ``helpers.sem_rede()`` activo em todos os pedidos (nada de Ollama :11434,
  backend :8000, visao :8081, Gmail, YouTube ou Internet);
* ``subprocess.run`` mockado nos testes de /code_lint (nunca executamos o
  "python" do PATH, que neste Windows e o alias de 0 bytes da Microsoft Store);
* nenhum teste chama rotas destrutivas a nao ser com payload que tem de falhar a
  validacao ANTES de executar.

Nota importante sobre ``sem_rede()`` + ``TestClient``: no Windows, o event loop
Proactor cria um socketpair (que faz ``connect``) ao ser criado. Por isso o
``TestClient`` e aberto como context manager ANTES de ``sem_rede()``; assim o
portal/loop e reutilizado e o bloqueio de rede continua a valer para os pedidos.
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests import helpers

try:  # pragma: no cover - depende do ambiente
    import agent as agent_module  # noqa: F401
    from tasks import task_store

    DISPONIVEL = True
    MOTIVO = ""
except Exception as exc:  # pragma: no cover
    DISPONIVEL = False
    MOTIVO = f"{type(exc).__name__}: {exc}"


# ============================================================
# Constantes do contrato
# ============================================================

CHAVES_WIDGET = {
    "state",
    "task_id",
    "objetivo",
    "passo_atual",
    "passo_num",
    "passo_total",
    "iniciado_em",
    "terminado_em",
    "resultado",
    "erro",
    "historico",
    "computer_activity",
}

DIAS_SEMANA = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")

REGEX_HORA = re.compile(
    r"^(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2}):(\d{2}) "
    r"\((segunda|terca|quarta|quinta|sexta|sabado|domingo)\)$"
)

# Rotas destrutivas/externas: so verificamos que o corpo vazio e recusado com 422
# (a validacao corre ANTES do handler, logo nada e executado).
ROTAS_CORPO_OBRIGATORIO = (
    "/open_url",
    "/search_google",
    "/type_text",
    "/press_key",
    "/wait",
    "/vision_locate",
    "/vision_click",
    "/vision_type",
    "/request_confirmation",
    "/email_send",
    "/email_search",
    "/email_reply",
    "/run_python",
    "/read_file",
    "/write_file",
    "/web_search",
    "/delete_file",
    "/create_dir",
    "/move_file",
    "/search_in_files",
    "/email_delete_by_search",
    "/pc_move_mouse",
    "/pc_type_text",
    "/pc_press_key",
    "/pc_hotkey",
    "/pc_scroll",
    "/pc_focus_window",
    "/pc_remove_chats_by_search",
    "/pc_rename_chat",
    "/code_generate",
    "/code_explain",
    "/code_analyze",
    "/code_review",
    "/code_refactor",
    "/code_optimize",
    "/code_convert",
    "/code_test",
    "/code_document",
    "/code_run",
    "/code_run_file",
    "/code_benchmark",
    "/code_dependencies",
    "/code_snippet",
    "/code_readme",
    "/youtube_transcript",
    "/youtube_summarize",
    "/youtube_ask",
    "/youtube_save",
    "/youtube_read",
    "/task_simple",
)


@unittest.skipUnless(DISPONIVEL, f"agent.py indisponivel: {MOTIVO}")
class BaseRotas(helpers.CasoBase):
    """Isolamento total por teste: tmp + sem rede + credenciais limpas."""

    @classmethod
    def setUpClass(cls):
        cls.agent = helpers.importar_agent()

    def setUp(self):
        super().setUp()  # helpers.AmbienteIsolado -> self.tmp

        # 1) Workspace e notas sempre em tmp (nunca no repo do utilizador).
        self._ws_ctx = helpers.workspace_temporario(self.agent)
        self.ws = self._ws_ctx.__enter__()
        self.addCleanup(lambda: self._ws_ctx.__exit__(None, None, None))

        self.notes = self.tmp / "notes.txt"
        self._notas_patch = mock.patch.object(self.agent, "NOTES_FILE", str(self.notes))
        self._notas_patch.start()
        self.addCleanup(self._notas_patch.stop)

        # 2) Credenciais ausentes: email/chat tem de cair no caminho de erro.
        self._env_patch = mock.patch.dict(
            os.environ,
            {"GMAIL_USER": "", "GMAIL_APP_PASSWORD": "", "OPENWEBUI_API_KEY": ""},
        )
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)
        for constante in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "OPENWEBUI_API_KEY"):
            if hasattr(self.agent, constante):
                patch = mock.patch.object(self.agent, constante, "")
                patch.start()
                self.addCleanup(patch.stop)

        # 3) TestClient (portal criado ANTES do bloqueio de rede) ...
        self._cliente_ctx = helpers.cliente_agent()
        self.client = self._cliente_ctx.__enter__()
        self.addCleanup(lambda: self._cliente_ctx.__exit__(None, None, None))

        # 4) ... e so depois a rede e bloqueada (LIFO: sem_rede sai primeiro).
        self._rede_ctx = helpers.sem_rede()
        self._rede_ctx.__enter__()
        self.addCleanup(lambda: self._rede_ctx.__exit__(None, None, None))

    # -- utilitarios ------------------------------------------------
    def _resposta_ok(self, resposta, rota: str) -> dict:
        """Valida o contrato minimo de uma resposta e devolve o corpo JSON."""
        self.assertIn(
            resposta.status_code,
            (200, 404, 422),
            f"{rota} devolveu {resposta.status_code}: nada pode ser 500 ({resposta.text[:200]})",
        )
        if resposta.status_code == 200:
            corpo = resposta.json()
            self.assertIsInstance(corpo, dict, f"{rota} nao devolveu um objecto JSON")
            self.assertIn("status", corpo, f"{rota} devolveu 200 sem a chave 'status'")
            self.assertIn(corpo["status"], ("ok", "erro", "aviso"))
            return corpo
        return {}

    def _criar_pendentes(self, quantidade: int):
        ids = []
        for i in range(quantidade):
            registo = task_store.criar_task(f"task pendente {i}")
            task_store.salvar_task(registo["task_id"], estado=task_store.ESTADO_PAUSADO)
            ids.append(registo["task_id"])
        return ids

    @staticmethod
    def _llm_falso(resposta="CODIGO-GERADO"):
        return helpers.HTTPFalso(resposta=helpers.RespostaHTTPFalsa({"response": resposta}))


# ============================================================
# GET / e GET /v1/models
# ============================================================

class RotasBasicasTestCase(BaseRotas):

    def test_get_raiz_contrato_exato(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "online", "agent": "computer-agent"})
        self.assertIn("application/json", r.headers.get("content-type", ""))

    def test_get_raiz_aceita_query_hostil(self):
        for params in (
            {"q": ""},
            {"q": "😀"},
            {"q": "a" * 4000},
            {"q": "'; DROP TABLE tasks; --"},
            {"a": ["1", "2"], "b": "null"},
            {"q": "\u2028\u0000\x01"},
        ):
            with self.subTest(params=str(params)[:40]):
                r = self.client.get("/", params=params)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "online")

    def test_metodos_errados_devolvem_405_e_nao_500(self):
        self.assertEqual(self.client.post("/", json={"a": 1}).status_code, 405)
        self.assertEqual(self.client.put("/").status_code, 405)
        self.assertEqual(self.client.delete("/").status_code, 405)

    def test_get_em_rotas_post_devolve_405(self):
        for rota in ("/save_note", "/read_notes", "/code_metrics", "/code_lint", "/get_current_time",
                     "/code_diff", "/code_regex", "/code_sql", "/code_scaffold"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 405)

    def test_v1_models_formato_openai(self):
        r = self.client.get("/v1/models")
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual(corpo["object"], "list")
        self.assertIsInstance(corpo["data"], list)
        self.assertTrue(corpo["data"], "lista de modelos vazia")
        modelo = corpo["data"][0]
        self.assertEqual(modelo["id"], "myra-agent")
        self.assertEqual(modelo["object"], "model")
        self.assertEqual(modelo["owned_by"], "myra")
        self.assertIsInstance(modelo["created"], int)

    def test_v1_models_estavel_em_10_chamadas(self):
        assinaturas = set()
        for _ in range(10):
            corpo = self.client.get("/v1/models").json()
            assinaturas.add(
                (corpo["object"], tuple(sorted((m["id"], m["object"], m["owned_by"]) for m in corpo["data"])))
            )
        self.assertEqual(len(assinaturas), 1, "o catalogo de modelos muda entre chamadas")

    def test_v1_models_ignora_query_e_headers_hostis(self):
        for cabecalhos in ({}, {"Accept": "text/html"}, {"Accept": "*/*", "X-Lixo": "a-b-c-'; DROP TABLE tasks;--"}):
            with self.subTest(cabecalhos=cabecalhos):
                r = self.client.get("/v1/models?debug=1", headers=cabecalhos)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["data"][0]["id"], "myra-agent")


# ============================================================
# GET /task_status
# ============================================================

class TaskStatusTestCase(BaseRotas):

    def test_chaves_estaveis_em_10_chamadas_seguidas(self):
        esperado = None
        for i in range(10):
            r = self.client.get("/task_status")
            self.assertEqual(r.status_code, 200)
            corpo = r.json()
            self.assertEqual(set(corpo.keys()), CHAVES_WIDGET, f"chaves diferentes na chamada {i}")
            if esperado is None:
                esperado = set(corpo.keys())
            self.assertEqual(set(corpo.keys()), esperado)

    def test_valores_coerentes_com_o_contrato(self):
        corpo = self.client.get("/task_status").json()
        self.assertIn(corpo["state"], ("idle", "running", "done", "error", "question"))
        self.assertIsInstance(corpo["historico"], list)
        self.assertIsInstance(corpo["passo_num"], int)
        self.assertIsInstance(corpo["passo_total"], int)
        self.assertGreaterEqual(corpo["passo_num"], 0)
        self.assertGreaterEqual(corpo["passo_total"], 0)

    def test_ignora_query_hostil_e_devolve_o_mesmo_estado(self):
        base = self.client.get("/task_status").json()
        for query in ("?state=done", "?task_id=" + "9" * 500, "?x=%F0%9F%98%80", "?x=1&y=2"):
            with self.subTest(query=query[:30]):
                r = self.client.get("/task_status" + query)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json(), base, "a query alterou o estado do widget")


# ============================================================
# GET /task_pendentes
# ============================================================

class TaskPendentesTestCase(BaseRotas):

    def test_base_vazia_devolve_lista_vazia(self):
        r = self.client.get("/task_pendentes")
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["tasks"], [])

    def test_lista_tasks_pausadas_com_metadados(self):
        ids = self._criar_pendentes(3)
        corpo = self.client.get("/task_pendentes").json()
        self.assertEqual(corpo["status"], "ok")
        devolvidos = [t["task_id"] for t in corpo["tasks"]]
        self.assertEqual(sorted(devolvidos), sorted(ids))
        for tarefa in corpo["tasks"]:
            self.assertIn("estado", tarefa)
            self.assertEqual(tarefa["estado"], task_store.ESTADO_PAUSADO)
            self.assertIn("objetivo", tarefa)

    def test_limite_e_respeitado(self):
        self._criar_pendentes(3)
        for limite, esperado in ((1, 1), (2, 2), (3, 3), (50, 3)):
            with self.subTest(limite=limite):
                corpo = self.client.get(f"/task_pendentes?limite={limite}").json()
                self.assertEqual(len(corpo["tasks"]), esperado)

    def test_limite_zero_devolve_lista_vazia(self):
        self._criar_pendentes(2)
        corpo = self.client.get("/task_pendentes?limite=0").json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["tasks"], [])

    def test_limite_invalido_devolve_422(self):
        for valor in ("abc", "1.5", "1e3", "", "true", "null", "0x10", "1;DROP TABLE tasks", "😀", "-", "1,5", "1 000", "0b1", "--1"):
            with self.subTest(valor=valor):
                r = self.client.get("/task_pendentes", params={"limite": valor})
                self.assertEqual(r.status_code, 422, f"limite={valor!r} devolveu {r.status_code}")
                self.assertIn("detail", r.json())

    def test_limite_hostil_nao_afecta_a_base(self):
        self._criar_pendentes(3)
        for valor in ("1;DROP TABLE tasks;--", "' OR 1=1 --", "\x00", "%"):
            with self.subTest(valor=valor):
                self.assertIn(self.client.get("/task_pendentes", params={"limite": valor}).status_code, (200, 422))
        self.assertEqual(len(self.client.get("/task_pendentes").json()["tasks"]), 3)

    def test_extremos_de_limite_nao_derrubam_o_backend(self):
        ids = self._criar_pendentes(3)
        # 2**63-1 e o maior inteiro que o SQLite aceita: tem de continuar a listar.
        corpo = self.client.get("/task_pendentes?limite=9223372036854775807").json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(len(corpo["tasks"]), len(ids))
        # Acima disso o limite e normalizado e todas as tasks existentes continuam visiveis.
        r = self.client.get("/task_pendentes?limite=9223372036854775808")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_limite_maior_que_int64_devolve_as_tasks(self):
        """Limites acima de int64 sao normalizados sem perder tasks existentes."""
        self._criar_pendentes(3)
        corpo = self.client.get("/task_pendentes?limite=9223372036854775808").json()
        self.assertEqual(len(corpo["tasks"]), 3, "limite enorme perdeu tasks existentes")

    def test_limite_negativo_e_rejeitado(self):
        """Valores negativos devem ser rejeitados pelo contrato HTTP (422)."""
        self._criar_pendentes(3)
        self.assertEqual(len(self.client.get("/task_pendentes?limite=1").json()["tasks"]), 1)
        r = self.client.get("/task_pendentes?limite=-1")
        self.assertEqual(r.status_code, 422, "limite negativo deveria ser rejeitado")
        self.assertIn("detail", r.json())


# ============================================================
# GET /task_detalhe/{task_id}
# ============================================================

class TaskDetalheTestCase(BaseRotas):

    def test_task_inexistente_devolve_erro_estruturado(self):
        r = self.client.get("/task_detalhe/task-que-nao-existe")
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/task_detalhe")
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("nao encontrada", corpo["result"])

    def test_task_existente_traz_historico_e_eventos(self):
        registo = task_store.criar_task("com detalhe")
        task_store.salvar_task(
            registo["task_id"],
            passo_atual=1,
            historico=[{"passo": 1, "ferramenta": "get_current_time", "ok": True}],
        )
        task_store.registrar_evento(registo["task_id"], "passo", "get_current_time", passo=1)

        r = self.client.get(f"/task_detalhe/{registo['task_id']}")
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/task_detalhe")
        self.assertEqual(corpo["status"], "ok")
        tarefa = corpo["task"]
        self.assertEqual(tarefa["task_id"], registo["task_id"])
        self.assertEqual(tarefa["objetivo"], "com detalhe")
        self.assertEqual(len(tarefa["historico"]), 1)
        self.assertEqual(tarefa["historico"][0]["ferramenta"], "get_current_time")
        self.assertEqual(len(tarefa["eventos"]), 1)
        self.assertEqual(tarefa["eventos"][0]["tipo"], "passo")

    def test_task_id_vazio_nao_define_rota(self):
        self.assertEqual(self.client.get("/task_detalhe/").status_code, 404)

    def test_task_ids_hostis_nao_produzem_500(self):
        hostis = [
            "notação-😀",
            "'; DROP TABLE tasks; --",
            "a" * 5000,
            "%00",
            "../../../etc/passwd",
            "task%20com%20espacos",
            "🐍" * 200,
            "%F0%9F%98%80",
        ]
        for task_id in hostis:
            with self.subTest(task_id=task_id[:24]):
                r = self.client.get("/task_detalhe/" + task_id)
                self.assertIn(r.status_code, (200, 404), f"id hostil devolveu {r.status_code}")
                if r.status_code == 200:
                    corpo = r.json()
                    self.assertIn("status", corpo)
                    self.assertEqual(corpo["status"], "erro")

    def test_ids_hostis_nao_corrompem_a_base(self):
        registo = task_store.criar_task("intacta")
        task_store.salvar_task(registo["task_id"], estado=task_store.ESTADO_PAUSADO)
        for task_id in ("'; DELETE FROM tasks; --", "%00", "😀"):
            self.client.get("/task_detalhe/" + task_id)
        r = self.client.get(f"/task_detalhe/{registo['task_id']}")
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["task"]["objetivo"], "intacta")


# ============================================================
# POST /get_current_time
# ============================================================

class GetCurrentTimeTestCase(BaseRotas):

    def _validar_hora(self, texto: str):
        casado = REGEX_HORA.match(texto)
        self.assertIsNotNone(casado, f"formato inesperado: {texto!r}")
        dia, mes, ano, hora, minuto, segundo, dia_semana = casado.groups()
        marca = datetime.datetime(int(ano), int(mes), int(dia), int(hora), int(minuto), int(segundo))
        agora = datetime.datetime.now()
        self.assertLess(abs((agora - marca).total_seconds()), 120, "hora devolvida fora da janela")
        self.assertEqual(dia_semana, DIAS_SEMANA[marca.weekday()], "dia da semana incorrecto")

    def test_formato_e_valor_do_timestamp(self):
        r = self.client.post("/get_current_time")
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/get_current_time")
        self.assertEqual(corpo["status"], "ok")
        self._validar_hora(corpo["result"])

    def test_aceita_corpo_ausente_lixo_e_json_invalido(self):
        casos = [
            {},
            None,
            {"foo": "bar"},
            {"texto": "ignorado"},
            {"nested": {"a": [1, 2, 3]}},
        ]
        for payload in casos:
            with self.subTest(payload=payload):
                if payload is None:
                    r = self.client.post("/get_current_time")
                else:
                    r = self.client.post("/get_current_time", json=payload)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "ok")
                self._validar_hora(r.json()["result"])

        r = self.client.post(
            "/get_current_time",
            content=b"{isto nao e json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(r.status_code, 200)
        self._validar_hora(r.json()["result"])

    def test_chamadas_repetidas_mantem_o_formato(self):
        for _ in range(5):
            self._validar_hora(self.client.post("/get_current_time").json()["result"])


# ============================================================
# POST /save_note e POST /read_notes
# ============================================================

class NotasTestCase(BaseRotas):

    def test_ciclo_salvar_e_ler(self):
        r = self.client.post("/save_note", json={"texto": "comprar pao"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/save_note")
        self.assertEqual(corpo["status"], "ok")
        self.assertIn(str(self.notes), corpo["result"])
        self.assertTrue(self.notes.is_file(), "a nota nao foi persistida")

        r = self.client.post("/read_notes")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("comprar pao", r.json()["result"])

    def test_campos_em_falta_e_tipos_errados_devolvem_422(self):
        casos = [
            {},
            {"texto": None},
            {"texto": 123},
            {"texto": 1.5},
            {"texto": True},
            {"texto": ["a"]},
            {"texto": {"a": 1}},
            {"outro": "sem texto"},
        ]
        for payload in casos:
            with self.subTest(payload=payload):
                r = self.client.post("/save_note", json=payload)
                self.assertEqual(r.status_code, 422, f"{payload} devolveu {r.status_code}")
                self.assertIn("detail", r.json())

        # corpo totalmente ausente
        self.assertEqual(self.client.post("/save_note").status_code, 422)
        # JSON invalido
        self.assertEqual(
            self.client.post(
                "/save_note", content=b"{quebrado", headers={"Content-Type": "application/json"}
            ).status_code,
            422,
        )

    def test_texto_unicode_emoji_e_perigoso_e_persistido(self):
        texto = "nota ção 😀\t\u2028 \\ %s; DROP TABLE tasks;-- \x00fim" % "x"
        r = self.client.post("/save_note", json={"texto": texto})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        conteudo = self.notes.read_text(encoding="utf-8-sig")
        self.assertIn(texto, conteudo, "a nota nao foi gravada exactamente")

    def test_texto_muito_longo_e_gravado(self):
        texto = "a" * 50000 + "😀"
        r = self.client.post("/save_note", json={"texto": texto})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertGreaterEqual(self.notes.stat().st_size, 50000)

    def test_nao_escreve_no_ficheiro_real_do_repo(self):
        real = Path(helpers.RAIZ_REPO) / "notes.txt"
        antes = real.stat().st_mtime_ns if real.exists() else None
        marcador = "nao-deve-aparecer-no-repo-😀"
        self.client.post("/save_note", json={"texto": marcador})
        depois = real.stat().st_mtime_ns if real.exists() else None
        self.assertEqual(antes, depois, "save_note escreveu no notes.txt real do repo")
        if real.exists():
            self.assertNotIn(marcador, real.read_text(encoding="utf-8-sig", errors="replace"))

    def test_erro_de_escrita_devolve_erro_estruturado(self):
        diretorio = self.tmp / "notes_como_diretorio"
        diretorio.mkdir()
        with mock.patch.object(self.agent, "NOTES_FILE", str(diretorio)):
            r = self.client.post("/save_note", json={"texto": "x"})
            self.assertEqual(r.status_code, 200)
            corpo = self._resposta_ok(r, "/save_note")
            self.assertEqual(corpo["status"], "erro")
            self.assertIn("Erro:", corpo["result"])

            r = self.client.post("/read_notes")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["status"], "erro")
            self.assertIn("Erro:", r.json()["result"])

    def test_campos_extra_sao_ignorados(self):
        r = self.client.post("/save_note", json={"texto": "com extras", "extra": {"a": 1}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIn("com extras", self.notes.read_text(encoding="utf-8-sig"))

    def test_read_notes_sem_ficheiro(self):
        self.assertFalse(self.notes.exists())
        r = self.client.post("/read_notes")
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/read_notes")
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("nenhuma nota", corpo["result"])

    def test_read_notes_com_ficheiro_vazio(self):
        self.notes.write_text("", encoding="utf-8")
        corpo = self.client.post("/read_notes").json()
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("nenhuma nota", corpo["result"])
        self.notes.write_text("   \n\t\n", encoding="utf-8")
        corpo = self.client.post("/read_notes").json()
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("nenhuma nota", corpo["result"])

    def test_read_notes_trunca_a_3000_caracteres(self):
        conteudo = "".join(f"{i:05d}" for i in range(1400))  # 7000 caracteres
        self.notes.write_text(conteudo, encoding="utf-8")
        resultado = self.client.post("/read_notes").json()["result"]
        self.assertEqual(len(resultado), 3000)
        self.assertEqual(resultado, conteudo[-3000:])

    def test_read_notes_ignora_corpo_invalido(self):
        self.notes.write_text("linha unica", encoding="utf-8")
        for kwargs in (
            {},
            {"json": {"a": 1}},
            {"content": b"nao e json", "headers": {"Content-Type": "application/json"}},
        ):
            with self.subTest(kwargs=list(kwargs)):
                r = self.client.post("/read_notes", **kwargs)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "ok")
                self.assertIn("linha unica", r.json()["result"])

    @unittest.expectedFailure
    def test_texto_vazio_e_rejeitado(self):
        """BUG: /save_note aceita texto="" e grava uma nota em branco.

        SaveNote.texto nao tem min_length (ao contrario de TaskResumeRequest /
        VisionLocateRequest, que usam Field(..., min_length=1)): um payload
        semanticamente vazio e persistido como "[timestamp] " no NOTES_FILE e
        responde 200 {"status": "ok"}.
        """
        r = self.client.post("/save_note", json={"texto": ""})
        self.assertEqual(r.status_code, 422, "texto vazio foi aceite e gravado (BUG)")


# ============================================================
# POST /code_metrics
# ============================================================

class CodeMetricsTestCase(BaseRotas):

    @staticmethod
    def _numeros(resultado: str) -> dict:
        valores = {}
        for chave, padrao in (
            ("total", r"Total de linhas: (\d+)"),
            ("codigo", r"Linhas de codigo: (-?\d+)"),
            ("branco", r"Linhas em branco: (\d+)"),
            ("comentario", r"Linhas de comentario: (\d+)"),
            ("caracteres", r"Total de caracteres: (\d+)"),
        ):
            casado = re.search(padrao, resultado)
            assert casado, f"campo {chave} ausente em {resultado!r}"
            valores[chave] = int(casado.group(1))
        return valores

    def test_contagem_exacta(self):
        codigo = "# comentario\nx = 1\n\nprint(x)"
        r = self.client.post("/code_metrics", json={"codigo": codigo})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_metrics")
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(
            self._numeros(corpo["result"]),
            {"total": 4, "codigo": 2, "branco": 1, "comentario": 1, "caracteres": len(codigo)},
        )

    def test_codigo_vazio(self):
        corpo = self.client.post("/code_metrics", json={"codigo": ""}).json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(
            self._numeros(corpo["result"]),
            {"total": 1, "codigo": 0, "branco": 1, "comentario": 0, "caracteres": 0},
        )

    def test_apenas_comentarios(self):
        codigo = "# um\n# dois"
        numeros = self._numeros(self.client.post("/code_metrics", json={"codigo": codigo}).json()["result"])
        self.assertEqual(numeros["comentario"], 2)
        self.assertEqual(numeros["codigo"], 0)

    def test_unicode_conta_code_points(self):
        codigo = "😀\n# ção"
        numeros = self._numeros(self.client.post("/code_metrics", json={"codigo": codigo}).json()["result"])
        self.assertEqual(numeros["caracteres"], len(codigo))
        self.assertEqual(numeros["total"], 2)
        self.assertEqual(numeros["comentario"], 1)

    def test_codigo_gigante_nao_derruba(self):
        codigo = "x = 1\n" * 20000
        r = self.client.post("/code_metrics", json={"codigo": codigo})
        self.assertEqual(r.status_code, 200)
        numeros = self._numeros(r.json()["result"])
        self.assertEqual(numeros["total"], 20001)
        self.assertEqual(numeros["caracteres"], len(codigo))

    def test_campos_em_falta_e_tipos_errados_devolvem_422(self):
        casos = [
            {},
            {"codigo": None},
            {"codigo": 1},
            {"codigo": ["x"]},
            {"codigo": {"a": 1}},
            {"codigo": True},
            {"codigo": "x", "contexto": 5},
            {"codigo": "x", "contexto": None},
            {"codigo": "x", "contexto": ["a"]},
        ]
        for payload in casos:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/code_metrics", json=payload).status_code, 422)
        self.assertEqual(self.client.post("/code_metrics").status_code, 422)

    def test_campos_extra_ignorados_e_codigo_perigoso(self):
        payload = {"codigo": "\x00; DROP TABLE tasks; -- 😀", "extra": 1, "kwargs": {"a": 1}}
        corpo = self.client.post("/code_metrics", json=payload).json()
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("Total de linhas: 1", corpo["result"])

    def test_nao_chama_llm_nem_rede(self):
        with self._llm_falso() as http:
            r = self.client.post("/code_metrics", json={"codigo": "x = 1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(http.pedidos, [], "/code_metrics contactou o Ollama")


# ============================================================
# POST /code_lint
# ============================================================

class CodeLintTestCase(BaseRotas):

    # subprocess.run e SEMPRE mockado: neste Windows "python" resolve para o
    # alias de 0 bytes da Microsoft Store (nunca executamos esse binario).
    def test_ok_quando_o_compilador_aceita(self):
        falso = subprocess.CompletedProcess(["python"], 0, "", "")
        with mock.patch.object(self.agent.subprocess, "run", return_value=falso):
            r = self.client.post("/code_lint", json={"codigo": "x = 1\n"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_lint")
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("Sem erros de sintaxe", corpo["result"])

    def test_erro_de_sintaxe_devolve_status_erro(self):
        falso = subprocess.CompletedProcess(["python"], 1, "", "  File \"x.py\", line 1\nSyntaxError: bad")
        with mock.patch.object(self.agent.subprocess, "run", return_value=falso):
            r = self.client.post("/code_lint", json={"codigo": "x =="})
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("SyntaxError", corpo["result"])

    def test_stderr_muito_longo_e_truncado(self):
        falso = subprocess.CompletedProcess(["python"], 1, "", "E" * 5000)
        with mock.patch.object(self.agent.subprocess, "run", return_value=falso):
            corpo = self.client.post("/code_lint", json={"codigo": "x =="}).json()
        self.assertEqual(corpo["status"], "erro")
        self.assertLessEqual(len(corpo["result"]), 2100, "stderr nao foi truncado")

    def test_timeout_nao_produz_500(self):
        with mock.patch.object(
            self.agent.subprocess, "run", side_effect=subprocess.TimeoutExpired("python", 10)
        ):
            r = self.client.post("/code_lint", json={"codigo": "while True: pass"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_lint")
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("Timeout", corpo["result"])

    def test_interpretador_ausente_nao_produz_500(self):
        with mock.patch.object(self.agent.subprocess, "run", side_effect=FileNotFoundError("python")):
            r = self.client.post("/code_lint", json={"codigo": "x = 1"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_lint")
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("FileNotFoundError", corpo["result"])

    def test_escreve_ficheiro_temporario_e_apaga_o(self):
        codigo = "# 😀 ção\nx = 1\n"
        visto = {}

        def falso_run(argv, **kwargs):
            caminho = argv[-1]
            visto["argv"] = argv
            visto["kwargs"] = kwargs
            visto["existia"] = os.path.exists(caminho)
            visto["conteudo"] = Path(caminho).read_text(encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(self.agent.subprocess, "run", side_effect=falso_run):
            r = self.client.post("/code_lint", json={"codigo": codigo})

        self.assertEqual(r.status_code, 200)
        self.assertTrue(visto["existia"], "o temporario nao existia quando o compilador correu")
        self.assertEqual(visto["conteudo"], codigo)
        self.assertTrue(visto["argv"][-1].endswith(".py"))
        self.assertNotIn("shell", visto["kwargs"])
        self.assertFalse(os.path.exists(visto["argv"][-1]), "ficheiro temporario deixado para tras")

    def test_interpretador_e_aceite_apenas_sem_shell(self):
        with mock.patch.object(self.agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as m:
            self.client.post("/code_lint", json={"codigo": "x = 1"})
        kwargs = m.call_args.kwargs
        self.assertFalse(kwargs.get("shell", False), "codigo do utilizador executado via shell")
        self.assertEqual(kwargs.get("timeout"), 10)

    def test_campos_em_falta_e_tipos_errados_devolvem_422(self):
        for payload in ({}, {"codigo": None}, {"codigo": 5}, {"codigo": ["x"]}, {"codigo": {"a": 1}}):
            with self.subTest(payload=payload):
                with mock.patch.object(self.agent.subprocess, "run") as m:
                    self.assertEqual(self.client.post("/code_lint", json=payload).status_code, 422)
                self.assertFalse(m.called, "a validacao correu depois de executar o compilador")
        self.assertEqual(self.client.post("/code_lint").status_code, 422)

    @unittest.expectedFailure
    def test_usa_o_interpretador_da_venv(self):
        """BUG: /code_lint executa o literal "python" do PATH em vez de sys.executable.

        Neste ambiente ``shutil.which("python")`` devolve
        ``C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WindowsApps\\python.EXE``
        (alias de 0 bytes da Microsoft Store), pelo que o caminho de sucesso
        ("OK - Sem erros de sintaxe") nao e alcancavel com codigo valido. O mesmo
        acontece em /code_run, /code_benchmark e /code_run_file.
        """
        with mock.patch.object(
            self.agent.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")
        ) as m:
            self.client.post("/code_lint", json={"codigo": "x = 1"})
        argv = m.call_args.args[0]
        self.assertEqual(argv[0], sys.executable, f"interpretador errado: {argv[0]!r}")


# ============================================================
# POST /code_diff, /code_regex, /code_sql, /code_scaffold
# ============================================================

class RotasCodeLLMTestCase(BaseRotas):

    # -- caminho feliz -------------------------------------------------
    def test_code_diff_envia_os_dois_codigos_para_o_ollama(self):
        with self._llm_falso("DIFF") as http:
            r = self.client.post("/code_diff", json={"codigo_antigo": "a = 1", "codigo_novo": "a = 2"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_diff")
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["result"], "DIFF")
        self.assertEqual(len(http.pedidos), 1)
        self.assertEqual(http.ultimo["url"], "http://127.0.0.1:11434/api/generate")
        payload = http.ultimo["payload"]
        self.assertEqual(payload["model"], self.agent.CODE_MODEL_PRIMARY)
        self.assertFalse(payload["stream"])
        self.assertIn("a = 1", payload["prompt"])
        self.assertIn("a = 2", payload["prompt"])

    def test_code_regex_envia_a_descricao(self):
        with self._llm_falso("REGEX") as http:
            corpo = self.client.post("/code_regex", json={"descricao": "email valido"}).json()
        self.assertEqual(corpo["status"], "ok")
        self.assertIn("email valido", http.ultimo["payload"]["prompt"])

    def test_code_sql_usa_dialeto_por_omissao_e_personalizado(self):
        with self._llm_falso("SQL") as http:
            self.client.post("/code_sql", json={"descricao": "contar utilizadores"})
            self.assertIn("postgresql", http.ultimo["payload"]["prompt"])
            self.client.post("/code_sql", json={"descricao": "contar", "dialeto": "mysql"})
            self.assertIn("mysql", http.ultimo["payload"]["prompt"])
            self.assertIn("contar utilizadores", http.pedidos[0]["payload"]["prompt"])

    def test_code_scaffold_usa_nome_por_omissao(self):
        with self._llm_falso("SCAFFOLD") as http:
            self.client.post("/code_scaffold", json={"tipo": "fastapi"})
            prompt = http.ultimo["payload"]["prompt"]
            self.assertIn("fastapi", prompt)
            self.assertIn("meu_projeto", prompt)
            self.client.post("/code_scaffold", json={"tipo": "cli", "nome": "myra-😀"})
            self.assertIn("myra-😀", http.ultimo["payload"]["prompt"])

    def test_unicode_e_caracteres_perigosos_chegam_intactos_ao_prompt(self):
        descricao = "criar regex para 😀 ção\n\\x00\u2028 ' OR 1=1 --"
        with self._llm_falso() as http:
            self.client.post("/code_regex", json={"descricao": descricao})
        self.assertIn(descricao, http.ultimo["payload"]["prompt"])

    def test_prompts_muito_longos_nao_derrubam(self):
        grande = "a" * 20000
        with self._llm_falso() as http:
            for rota, payload in (
                ("/code_regex", {"descricao": grande}),
                ("/code_sql", {"descricao": grande}),
                ("/code_diff", {"codigo_antigo": grande, "codigo_novo": grande}),
                ("/code_scaffold", {"tipo": "x", "nome": "n" * 500}),
            ):
                with self.subTest(rota=rota):
                    corpo = self.client.post(rota, json=payload).json()
                    self.assertEqual(corpo["status"], "ok")
        self.assertEqual(len(http.pedidos), 4)

    # -- caminhos de erro ----------------------------------------------
    def test_ollama_indisponivel_devolve_erro_estruturado(self):
        with helpers.HTTPFalso(erro=OSError("connection refused")) as http:
            r = self.client.post("/code_regex", json={"descricao": "x"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_regex")
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("Nenhum modelo disponivel", corpo["result"])
        self.assertEqual(len(http.pedidos), 2, "devia tentar o modelo primario e o fallback")

    def test_sem_mock_e_com_rede_bloqueada_devolve_erro(self):
        """sem_rede() activo e urlopen real: a rota tem de responder, nao rebentar."""
        r = self.client.post("/code_scaffold", json={"tipo": "cli"})
        self.assertEqual(r.status_code, 200)
        corpo = self._resposta_ok(r, "/code_scaffold")
        self.assertEqual(corpo["status"], "erro")
        self.assertIn("Nenhum modelo disponivel", corpo["result"])

    def test_json_invalido_do_ollama_devolve_erro(self):
        with helpers.HTTPFalso(resposta=helpers.RespostaHTTPFalsa("isto nao e json")) as http:
            corpo = self.client.post("/code_sql", json={"descricao": "x"}).json()
        self.assertEqual(corpo["status"], "erro")
        self.assertEqual(len(http.pedidos), 2)

    def test_resposta_vazia_do_ollama_devolve_erro(self):
        for resposta in ({"response": ""}, {}, {"response": None}, {"outro": "campo"}):
            with self.subTest(resposta=resposta):
                with helpers.HTTPFalso(resposta=helpers.RespostaHTTPFalsa(resposta)) as http:
                    corpo = self.client.post("/code_regex", json={"descricao": "x"}).json()
                self.assertEqual(corpo["status"], "erro")
                self.assertEqual(len(http.pedidos), 2)

    def test_http_500_do_ollama_devolve_erro(self):
        import urllib.error

        erro = urllib.error.HTTPError("http://127.0.0.1:11434", 500, "erro interno", {}, None)
        with helpers.HTTPFalso(erro=erro):
            r = self.client.post("/code_diff", json={"codigo_antigo": "a", "codigo_novo": "b"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "erro")

    def test_resposta_gigante_e_preservada(self):
        gigante = "L" * 120000
        with self._llm_falso(gigante):
            corpo = self.client.post("/code_regex", json={"descricao": "x"}).json()
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["result"], gigante)

    # -- validacao ------------------------------------------------------
    def test_campos_em_falta_e_tipos_errados_devolvem_422(self):
        casos = [
            ("/code_diff", {}),
            ("/code_diff", {"codigo_antigo": "a"}),
            ("/code_diff", {"codigo_novo": "b"}),
            ("/code_diff", {"codigo_antigo": 1, "codigo_novo": 2}),
            ("/code_diff", {"codigo_antigo": None, "codigo_novo": None}),
            ("/code_diff", {"codigo_antigo": ["a"], "codigo_novo": {"b": 1}}),
            ("/code_regex", {}),
            ("/code_regex", {"descricao": None}),
            ("/code_regex", {"descricao": 42}),
            ("/code_regex", {"descricao": ["x"]}),
            ("/code_sql", {}),
            ("/code_sql", {"descricao": "x", "dialeto": 7}),
            ("/code_sql", {"descricao": None}),
            ("/code_scaffold", {}),
            ("/code_scaffold", {"tipo": None}),
            ("/code_scaffold", {"tipo": ["x"]}),
            ("/code_scaffold", {"tipo": 1, "nome": 2}),
        ]
        for rota, payload in casos:
            with self.subTest(rota=rota, payload=payload):
                with helpers.HTTPFalso() as http:
                    r = self.client.post(rota, json=payload)
                self.assertEqual(r.status_code, 422, f"{rota} com {payload} devolveu {r.status_code}")
                self.assertEqual(http.pedidos, [], "chamou o LLM antes de validar o payload")

    def test_corpo_ausente_devolve_422_sem_chamar_o_llm(self):
        for rota in ("/code_diff", "/code_regex", "/code_sql", "/code_scaffold"):
            with self.subTest(rota=rota):
                with helpers.HTTPFalso() as http:
                    r = self.client.post(rota)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(http.pedidos, [])

    def test_json_invalido_no_pedido_devolve_422(self):
        for rota in ("/code_diff", "/code_regex", "/code_sql", "/code_scaffold"):
            with self.subTest(rota=rota):
                r = self.client.post(
                    rota, content=b"{nao-e-json", headers={"Content-Type": "application/json"}
                )
                self.assertEqual(r.status_code, 422)


# ============================================================
# Severidade extra: corpo vazio nas rotas destrutivas
# ============================================================

class RotasDestrutivasRecusamCorpoVazioTestCase(BaseRotas):

    def test_corpo_vazio_e_recusado_antes_de_executar(self):
        for rota in ROTAS_CORPO_OBRIGATORIO:
            with self.subTest(rota=rota):
                r = self.client.post(rota, json={})
                self.assertEqual(r.status_code, 422, f"{rota} aceitou corpo vazio ({r.status_code})")
                self.assertIn("detail", r.json())

    def test_corpo_totalmente_ausente_e_recusado(self):
        for rota in ("/delete_file", "/move_file", "/email_send", "/code_run", "/youtube_save", "/pc_type_text"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.post(rota).status_code, 422)

    @unittest.expectedFailure
    def test_pc_click_com_corpo_vazio_e_rejeitado(self):
        """BUG: /pc_click, /pc_double_click e /pc_right_click aceitam corpo vazio {}.

        ``PCClick`` tem ``x: int = None`` / ``y: int = None`` / ``button: str = "left"``:
        o payload vazio passa a validacao, a rota chama o executor real de rato e
        responde 200 {"status": "ok", "result": "Clique left em (None, None)"}
        (confirmado: /pc_double_click idem, /pc_right_click idem). Aqui o executor e
        substituido por um mock, por isso NADA e clicado no PC real -- as duas
        primeiras assercoes registam a evidencia de que o clique foi executado.
        """
        if not hasattr(self.agent, "_pc_click_fn"):
            self.skipTest("agent._pc_click_fn nao encontrado")
        with mock.patch.object(
            self.agent, "_pc_click_fn", return_value={"status": "ok", "result": "MOCK"}
        ) as falso:
            r = self.client.post("/pc_click", json={})
        # evidencia: o executor de clique foi mesmo invocado, com coordenadas None
        self.assertTrue(falso.called, "o executor de clique nao foi chamado")
        self.assertEqual(list(falso.call_args.args), [None, None, "left"])
        # contrato desejado: payload vazio recusado ANTES de executar
        self.assertEqual(r.status_code, 422, "corpo vazio aceite: clique real executado (BUG)")

    def test_rotas_de_email_sem_credenciais_caem_no_erro(self):
        for rota in ("/email_list", "/email_read", "/email_mark_read", "/email_move", "/email_delete"):
            with self.subTest(rota=rota):
                r = self.client.post(rota, json={})
                self.assertEqual(r.status_code, 200)
                corpo = self._resposta_ok(r, rota)
                self.assertEqual(corpo["status"], "erro", f"{rota} nao caiu no caminho de erro")
                self.assertIn("GMAIL_USER", corpo["result"])


# ============================================================
# Varredura: nenhum payload pode produzir 500
# ============================================================

class VarreduraSem500TestCase(BaseRotas):

    def test_matriz_de_payloads_hostis_nunca_produz_500(self):
        casos = [
            ("get", "/", None, None),
            ("get", "/" + "?" + "q=" + "😀" * 500, None, None),
            ("get", "/v1/models", None, None),
            ("get", "/task_status", None, None),
            ("get", "/task_pendentes", None, {"limite": "9" * 40}),
            ("get", "/task_pendentes", None, {"limite": "-3"}),
            ("get", "/task_pendentes", None, {"limite": "'; DROP TABLE tasks; --"}),
            ("get", "/task_detalhe/" + "a" * 3000, None, None),
            ("get", "/task_detalhe/%F0%9F%98%80%00%27", None, None),
            ("post", "/get_current_time", {}, None),
            ("post", "/get_current_time", {"x": [1, 2, {"y": None}]}, None),
            ("post", "/save_note", {"texto": "\x00\x01😀' OR 1=1 --"}, None),
            ("post", "/save_note", {"texto": "b" * 120000}, None),
            ("post", "/save_note", {"texto": "\u2028\u2029\u0000"}, None),
            ("post", "/read_notes", {"ignorado": "😀" * 1000}, None),
            ("post", "/code_metrics", {"codigo": "\x00" * 500}, None),
            ("post", "/code_metrics", {"codigo": "😀" * 5000}, None),
            ("post", "/code_metrics", {"codigo": "x = 1\r\n" * 3000}, None),
            ("post", "/code_lint", {"codigo": "😀 = 1"}, None),
            ("post", "/code_lint", {"codigo": "x = 1\n" * 4000}, None),
            ("post", "/code_diff", {"codigo_antigo": "\x00" * 10, "codigo_novo": "x" * 100000}, None),
            ("post", "/code_regex", {"descricao": "'; DROP TABLE tasks; --"}, None),
            ("post", "/code_regex", {"descricao": ""}, None),
            ("post", "/code_sql", {"descricao": "\u2028\u2029", "dialeto": "x" * 300}, None),
            ("post", "/code_sql", {"descricao": "😀", "dialeto": ""}, None),
            ("post", "/code_scaffold", {"tipo": "../../../etc/passwd", "nome": "\x00"}, None),
            ("post", "/code_scaffold", {"tipo": "t" * 300, "nome": "n" * 300}, None),
        ]

        completos = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(self.agent.subprocess, "run", return_value=completos), \
                helpers.HTTPFalso() as http:
            for metodo, rota, payload, params in casos:
                with self.subTest(rota=rota[:40], payload=str(payload)[:40]):
                    try:
                        if metodo == "get":
                            resposta = self.client.get(rota, params=params)
                        else:
                            resposta = self.client.post(rota, json=payload)
                    except Exception as exc:  # noqa: BLE001
                        self.fail(f"{metodo.upper()} {rota} levantou {type(exc).__name__}: {exc}")
                    self.assertIn(
                        resposta.status_code,
                        (200, 404, 422),
                        f"{metodo.upper()} {rota} devolveu {resposta.status_code}: {resposta.text[:200]}",
                    )
                    if resposta.status_code == 200 and rota not in ("/task_status", "/", "/v1/models"):
                        self.assertIn("status", resposta.json(), f"{rota} devolveu 200 sem 'status'")
        self.assertGreaterEqual(len(casos), 20)

    def test_nenhuma_rota_alvo_levanta_excepcao_com_payload_minimo(self):
        for rota, payload in (
            ("/save_note", {"texto": "ok"}),
            ("/code_metrics", {"codigo": "x = 1"}),
            ("/code_diff", {"codigo_antigo": "a", "codigo_novo": "b"}),
            ("/code_regex", {"descricao": "d"}),
            ("/code_sql", {"descricao": "d"}),
            ("/code_scaffold", {"tipo": "t"}),
        ):
            with self.subTest(rota=rota):
                completos = subprocess.CompletedProcess([], 0, "", "")
                with mock.patch.object(self.agent.subprocess, "run", return_value=completos), \
                        helpers.HTTPFalso():
                    r = self.client.post(rota, json=payload)
                self.assertEqual(r.status_code, 200)
                self.assertIn(r.json()["status"], ("ok", "erro"))

    @unittest.expectedFailure
    def test_rotas_de_browser_nao_deixam_escapar_excepcao(self):
        """BUG: nas rotas de browser o ``start_browser()`` esta FORA do try/except.

        Ex.: /click_element (agent.py:778), /go_back (agent.py:953) e /wait
        (agent.py:965) chamam ``start_browser()`` antes do try, por isso qualquer
        falha ao arrancar o Chrome/playwright propaga-se e o FastAPI responde 500
        em vez de {"status": "erro"}. Evidencia: a sonda exploratoria com
        sem_rede() activo levantou ``OSError`` do servidor em /click_element,
        /go_back, /read_page e /read_page_structured (o TestClient re-lanca a
        excepcao do handler, logo em producao seria um 500). Aqui ``start_browser``
        e mockado, por isso o Chrome nunca e tocado. (Rotas fora do grupo alvo.)
        """
        for rota, payload in (
            ("/click_element", {"text": "Entrar"}),
            ("/go_back", {}),
            ("/wait", {"seconds": 1}),
        ):
            with self.subTest(rota=rota):
                with mock.patch.object(
                    self.agent, "start_browser", side_effect=RuntimeError("chrome nao arrancou")
                ):
                    r = self.client.post(rota, json=payload)
                self.assertEqual(
                    r.status_code, 200, f"{rota} devolveu {r.status_code} (esperado erro estruturado)"
                )
                self.assertEqual(r.json()["status"], "erro")


if __name__ == "__main__":
    unittest.main()
