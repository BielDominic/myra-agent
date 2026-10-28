from unittest.mock import patch

import tasks.simple_task as simple_task


def test_diagnostic_with_explicit_no_weather_hides_weather_and_web_search_tools():
    original_tools = dict(simple_task.FERRAMENTAS_DISPONIVEIS)
    original_descriptions = dict(simple_task.FERRAMENTAS_DESCRICOES)
    captured = {}

    try:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.registrar_ferramenta("get_weather", lambda **kwargs: {"status": "ok"}, "weather")
        simple_task.registrar_ferramenta("browser_search_google", lambda **kwargs: {"status": "ok"}, "Google search")
        simple_task.registrar_ferramenta("read_file", lambda **kwargs: {"status": "ok"}, "read local file")

        def fake_llm(prompt, system):
            captured["prompt"] = prompt
            return '{"acao":"finalizar","motivo":"diagnostico pendente"}'

        objetivo = (
            "Diagnostique e corrija o erro de pesquisa jurídica. "
            "Inspecione o código e os logs, corrija a causa raiz. Não consulte o clima."
        )
        with patch.object(simple_task, "_llm", side_effect=fake_llm):
            decisao = simple_task._decidir_proximo_passo(objetivo, [])

        prompt = captured["prompt"]
        assert "get_weather:" not in prompt
        assert "browser_search_google:" not in prompt
        assert "read_file:" in prompt
        assert decisao["acao"] == "finalizar"
    finally:
        simple_task.FERRAMENTAS_DISPONIVEIS.clear()
        simple_task.FERRAMENTAS_DISPONIVEIS.update(original_tools)
        simple_task.FERRAMENTAS_DESCRICOES.clear()
        simple_task.FERRAMENTAS_DESCRICOES.update(original_descriptions)
