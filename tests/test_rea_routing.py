from unittest import mock

from tasks import simple_task


def test_status_rea_forca_chamada_da_ferramenta_mesmo_se_planner_promete():
    objetivo = "Verifique o status do REA usando a ferramenta rea_status e apresente os valores retornados, sem inventar resultados."
    original_tools = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
    original_descriptions = dict(simple_task.FERRAMENTAS_DESCRICOES)
    try:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.registrar_ferramenta("rea_status", lambda: {"status": "ok"}, "Consulta status REA")
        with mock.patch.object(simple_task, "_llm", side_effect=AssertionError("roteamento nao deve depender do LLM")):
            decisao = simple_task._decidir_proximo_passo(objetivo, [])
        assert decisao["acao"] == "chamar"
        assert decisao["ferramenta"] == "rea_status"
        assert decisao["args"] == {}
    finally:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(original_tools)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(original_descriptions)


def test_sintese_status_rea_entrega_valores_reais_sem_chamar_llm():
    objetivo = "Verifique o status do REA usando a ferramenta rea_status e apresente os valores retornados."
    retorno = {
        "status": "ok",
        "node_found": True,
        "npx_found": True,
        "node_version": "v24.20.0",
        "rea_package": "rea-agents@6.5.0",
        "allowed_roots": [r"C:\\computer-agent\\workspace"],
        "note": "O pacote REA so sera baixado pelo npx quando rea_analyze_javascript for chamado.",
    }
    historico = [{"ferramenta": "rea_status", "ok": True, "resultado": retorno, "args": {}, "passo": 1}]
    with mock.patch.object(simple_task, "_llm", side_effect=AssertionError("sintese nao deve depender do LLM")):
        resposta = simple_task._sintetizar(objetivo, historico)
    assert "Node.js encontrado: True" in resposta
    assert "npx encontrado: True" in resposta
    assert "v24.20.0" in resposta
    assert "rea-agents@6.5.0" in resposta
    assert r"C:\\computer-agent\\workspace" in resposta


def test_mcp_descobre_catalogo_e_esquemas_apenas_da_allowlist():
    from tasks import rea_tools

    tools = [
        {"name": "current_document", "description": "Read current document", "inputSchema": {"type": "object"}},
        {"name": "set_comment", "description": "Writes a comment", "inputSchema": {"type": "object"}},
    ]
    with mock.patch.object(rea_tools, "_run_mcp_bridge", return_value={"tools": tools}):
        result = rea_tools.rea_mcp_list_tools()

    assert result["status"] == "ok"
    assert result["tool_count"] == 2
    assert [item["name"] for item in result["read_only_tools"]] == ["current_document"]
    assert result["read_only_tools"][0]["inputSchema"] == {"type": "object"}


def test_mcp_bloqueia_ferramentas_fora_da_allowlist_sem_chamar_servidor():
    from tasks import rea_tools

    with mock.patch.object(rea_tools, "_run_mcp_bridge") as bridge:
        result = rea_tools.rea_mcp_call("set_comment", {"address": "0x1000", "comment": "x"})

    assert result["status"] == "erro"
    assert "nao autorizada" in result["result"]
    bridge.assert_not_called()


def test_mcp_call_valida_argumentos_e_limita_tamanho():
    from tasks import rea_tools

    assert rea_tools.rea_mcp_call("current_document", [])["status"] == "erro"
    assert rea_tools.rea_mcp_call("current_document", {"large": "x" * 17000})["status"] == "erro"


def test_mcp_javascript_rejeita_caminho_fora_das_raizes_autorizadas(tmp_path):
    from tasks import rea_tools

    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    with mock.patch.object(rea_tools, "_allowed_roots", return_value=[allowed.resolve()]), \
         mock.patch.object(rea_tools, "_run_mcp_bridge") as bridge:
        result = rea_tools.rea_mcp_call("analyze_javascript_application", {"input_path": str(outside)})

    assert result["status"] == "erro"
    assert "fora das raizes autorizadas" in result["result"]
    bridge.assert_not_called()


def test_mcp_call_invoca_apenas_ferramenta_allowlisted(tmp_path):
    from tasks import rea_tools

    # Isolate the test from a real active-target record left by an REA session.
    with mock.patch.object(rea_tools, "ACTIVE_TARGET_FILE", tmp_path / "missing-active-target.json"), \
         mock.patch.object(rea_tools, "_run_mcp_bridge", return_value={"result": {"content": [{"text": "document"}]}}) as bridge:
        result = rea_tools.rea_mcp_call("current_document", {})

    assert result["status"] == "ok"
    assert result["tool"] == "current_document"
    bridge.assert_called_once_with("call", {"name": "current_document", "arguments": {}})


def test_catalogo_rea_parseia_comandos_sem_executa_los():
    import json
    from types import SimpleNamespace
    from tasks import rea_tools

    payload = {
        "version": "incur.v1",
        "commands": [
            {"name": "analyze", "description": "Get an overview"},
            {"name": "inspect-artifact", "description": "Inspect a local artifact"},
        ],
    }
    with mock.patch.object(rea_tools, "_node_version", return_value=(24, 20, 0)), \
         mock.patch.object(rea_tools, "_npx_command", return_value=["npx"]), \
         mock.patch.object(
             rea_tools.subprocess, "run",
             return_value=SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
         ) as run:
        result = rea_tools.rea_catalog()

    assert result["status"] == "ok"
    assert result["command_count"] == 2
    assert result["commands"][0]["name"] == "analyze"
    assert result["commands"][1]["name"] == "inspect-artifact"
    assert run.call_args.kwargs["shell"] is False
    assert run.call_args.kwargs["timeout"] == 60


def test_pedido_catalogo_rea_rota_para_ferramenta_sem_llm():
    original_tools = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
    original_descriptions = dict(simple_task.FERRAMENTAS_DESCRICOES)
    try:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.registrar_ferramenta("rea_catalog", lambda: {"status": "ok"}, "Catalogo REA")
        objetivo = "Liste o catalogo de comandos do REA"
        with mock.patch.object(simple_task, "_llm", side_effect=AssertionError("nao deve depender do LLM")):
            decisao = simple_task._decidir_proximo_passo(objetivo, [])
        assert decisao["acao"] == "chamar"
        assert decisao["ferramenta"] == "rea_catalog"
        assert decisao["args"] == {}
    finally:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(original_tools)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(original_descriptions)


def test_mcp_static_binary_tools_validate_authorized_existing_file(tmp_path):
    from tasks import rea_tools

    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    binary = allowed / "sample.exe"
    binary.write_bytes(b"MZ\x00\x00")
    denied = outside / "other.exe"
    denied.write_bytes(b"MZ\x00\x00")

    with mock.patch.object(rea_tools, "_allowed_roots", return_value=[allowed.resolve()]), \
         mock.patch.object(rea_tools, "_run_mcp_bridge", return_value={"result": {"content": [{"text": "Evidence"}]}}) as bridge:
        accepted = rea_tools.rea_mcp_call("inspect_go_binary", {"path": str(binary)})
        rejected = rea_tools.rea_mcp_call("inspect_rust_binary", {"path": str(denied)})

    assert accepted["status"] == "ok"
    assert bridge.call_count == 1
    assert bridge.call_args.args[1]["arguments"]["path"] == str(binary.resolve())
    assert rejected["status"] == "erro"
    assert "fora das raizes autorizadas" in rejected["result"]
