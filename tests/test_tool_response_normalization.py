import json

import pytest
from pydantic import Field
from pydantic.fields import FieldInfo

from tools.codeagent import _normalizar_payload as normalizar_payload_code
from tools.codeagent import _normalizar_resposta as normalizar_resposta_code
from tools.browseragent import _normalizar_payload as normalizar_payload_browser
from tools.browseragent import _normalizar_resposta as normalizar_resposta_browser


@pytest.mark.parametrize("normalizar", [normalizar_payload_code, normalizar_payload_browser])
def test_payload_fieldinfo_default_is_json_serializable(normalizar):
    payload = {"required": Field(...), "default": Field(20), "plain": "ok"}
    normalized = normalizar(payload)
    assert normalized == {"required": None, "default": 20, "plain": "ok"}
    assert isinstance(payload["required"], FieldInfo)
    assert json.loads(json.dumps(normalized)) == normalized


@pytest.mark.parametrize("normalizar", [normalizar_payload_code, normalizar_payload_browser])
def test_payload_keeps_nested_json_values(normalizar):
    assert normalizar({"items": [1, {"enabled": True}], "none": None}) == {
        "items": [1, {"enabled": True}], "none": None
    }


@pytest.mark.parametrize("normalizar", [normalizar_resposta_code, normalizar_resposta_browser])
def test_response_requires_json_object(normalizar):
    assert normalizar(["not", "an", "object"]) == {
        "status": "erro", "result": "Erro: resposta invalida do agent.py (JSON nao e objeto)"
    }


@pytest.mark.parametrize("normalizar", [normalizar_resposta_code, normalizar_resposta_browser])
def test_response_normalizes_null_result_without_mutating_input(normalizar):
    original = {"status": "ok", "result": None, "extra": 1}
    normalized = normalizar(original)
    assert normalized == {"status": "ok", "result": "sem resultado", "extra": 1}
    assert original["result"] is None


@pytest.mark.parametrize("normalizar", [normalizar_resposta_code, normalizar_resposta_browser])
def test_response_preserves_valid_payload(normalizar):
    original = {"status": "ok", "result": "done", "metadata": {"count": 2}}
    assert normalizar(original) == original
