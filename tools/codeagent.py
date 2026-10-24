import requests
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo


def _normalizar_payload(payload: dict) -> dict:
    """Converte defaults Pydantic FieldInfo em valores JSON serializaveis."""
    normalizado = {}
    for chave, valor in payload.items():
        if isinstance(valor, FieldInfo):
            if valor.default is None:
                continue
            valor = None if type(valor.default).__name__ == "PydanticUndefinedType" else valor.default
        normalizado[chave] = valor
    return normalizado


def _normalizar_resposta(resposta) -> dict:
    """Garante contrato de objeto JSON e resultado textual para o consumidor."""
    if not isinstance(resposta, dict):
        return {"status": "erro", "result": "Erro: resposta invalida do agent.py (JSON nao e objeto)"}
    resultado = resposta.get("result", "sem resultado")
    if resultado is None:
        resposta = dict(resposta)
        resposta["result"] = "sem resultado"
    return resposta


class Tools:
    def __init__(self):
        self.base_url = "http://host.docker.internal:8000"

    def _post(self, rota: str, payload: dict) -> dict:
        try:
            payload = _normalizar_payload(payload)
            r = requests.post(f"{self.base_url}{rota}", json=payload, timeout=300)
            r.raise_for_status()
            return _normalizar_resposta(r.json())
        except requests.exceptions.ConnectionError:
            return {"status": "erro", "result": "agent.py inacessivel"}
        except Exception as e:
            return {"status": "erro", "result": f"Erro: {type(e).__name__}"}

    # ============================================================
    # EXECUCAO
    # ============================================================

    def code_run(
        self, codigo: str = Field(..., description="Codigo Python a executar")
    ) -> str:
        """Executa codigo Python e retorna stdout/stderr/exit code.
        Use quando o usuario pedir para rodar/testar um codigo Python."""
        r = self._post("/code_run", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_run_file(
        self,
        caminho: str = Field(..., description="Caminho do arquivo em workspace/code/"),
        args: list = Field([], description="Argumentos de linha de comando"),
    ) -> str:
        """Executa um arquivo Python salvo em workspace/code/."""
        r = self._post("/code_run_file", {"caminho": caminho, "args": args})
        return r.get("result", "sem resultado")

    def code_benchmark(
        self,
        codigo: str = Field(..., description="Codigo Python a medir"),
        repeticoes: int = Field(10, description="Numero de execucoes"),
    ) -> str:
        """Mede o tempo de execucao do codigo (N execucoes, retorna media/min/max)."""
        r = self._post("/code_benchmark", {"codigo": codigo, "repeticoes": repeticoes})
        return r.get("result", "sem resultado")

    # ============================================================
    # ANALISE
    # ============================================================

    def code_explain(
        self, codigo: str = Field(..., description="Codigo a explicar")
    ) -> str:
        """Explica o que o codigo faz, linha por linha."""
        r = self._post("/code_explain", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_analyze(
        self, codigo: str = Field(..., description="Codigo a analisar")
    ) -> str:
        """Analisa bugs, problemas de seguranca, performance e boas praticas."""
        r = self._post("/code_analyze", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_review(
        self, codigo: str = Field(..., description="Codigo a revisar")
    ) -> str:
        """Faz code review profissional com sugestoes de melhoria."""
        r = self._post("/code_review", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_lint(
        self, codigo: str = Field(..., description="Codigo a validar")
    ) -> str:
        """Valida sintaxe do codigo Python (py_compile)."""
        r = self._post("/code_lint", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_metrics(
        self, codigo: str = Field(..., description="Codigo a medir")
    ) -> str:
        """Mede LOC, linhas comentadas, caracteres."""
        r = self._post("/code_metrics", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_dependencies(
        self, codigo: str = Field(..., description="Codigo a analisar")
    ) -> str:
        """Lista dependencias externas necessarias (com 'pip install' pronto)."""
        r = self._post("/code_dependencies", {"codigo": codigo})
        return r.get("result", "sem resultado")

    # ============================================================
    # GERACAO
    # ============================================================

    def code_generate(
        self,
        descricao: str = Field(..., description="O que o codigo deve fazer"),
        linguagem: str = Field("python", description="Linguagem de programacao"),
    ) -> str:
        """Gera codigo do zero a partir de uma descricao.
        Use quando o usuario pedir para criar/escrever codigo novo."""
        r = self._post(
            "/code_generate", {"descricao": descricao, "linguagem": linguagem}
        )
        return r.get("result", "sem resultado")

    def code_snippet(
        self,
        descricao: str = Field(..., description="O que o snippet deve fazer"),
        linguagem: str = Field("python", description="Linguagem"),
    ) -> str:
        """Cria um pequeno snippet de codigo pronto para colar."""
        r = self._post(
            "/code_snippet", {"descricao": descricao, "linguagem": linguagem}
        )
        return r.get("result", "sem resultado")

    def code_scaffold(
        self,
        tipo: str = Field(
            ..., description="Tipo de projeto (ex: 'api fastapi', 'cli tool')"
        ),
        nome: str = Field("meu_projeto", description="Nome do projeto"),
    ) -> str:
        """Cria a estrutura inicial (scaffold) de um projeto completo."""
        r = self._post("/code_scaffold", {"tipo": tipo, "nome": nome})
        return r.get("result", "sem resultado")

    def code_regex(
        self, descricao: str = Field(..., description="O que a regex deve capturar")
    ) -> str:
        """Cria uma expressao regular a partir de uma descricao."""
        r = self._post("/code_regex", {"descricao": descricao})
        return r.get("result", "sem resultado")

    def code_sql(
        self,
        descricao: str = Field(..., description="O que a query SQL deve fazer"),
        dialeto: str = Field(
            "postgresql", description="Dialeto SQL (postgresql, mysql, sqlite, etc)"
        ),
    ) -> str:
        """Cria uma query SQL a partir de uma descricao."""
        r = self._post("/code_sql", {"descricao": descricao, "dialeto": dialeto})
        return r.get("result", "sem resultado")

    def code_readme(
        self, codigo: str = Field(..., description="Codigo ou projeto")
    ) -> str:
        """Gera um README.md profissional a partir do codigo."""
        r = self._post("/code_readme", {"codigo": codigo})
        return r.get("result", "sem resultado")

    # ============================================================
    # REFATORACAO
    # ============================================================

    def code_refactor(
        self,
        codigo: str = Field(..., description="Codigo a refatorar"),
        objetivo: str = Field(
            ..., description="Objetivo (ex: 'usar list comprehension')"
        ),
    ) -> str:
        """Refatora o codigo conforme um objetivo especifico."""
        r = self._post("/code_refactor", {"codigo": codigo, "objetivo": objetivo})
        return r.get("result", "sem resultado")

    def code_optimize(
        self, codigo: str = Field(..., description="Codigo a otimizar")
    ) -> str:
        """Otimiza a performance do codigo mantendo o comportamento."""
        r = self._post("/code_optimize", {"codigo": codigo})
        return r.get("result", "sem resultado")

    def code_convert(
        self,
        codigo: str = Field(..., description="Codigo a converter"),
        linguagem_destino: str = Field(
            ..., description="Linguagem destino (ex: javascript, java)"
        ),
        linguagem_origem: str = Field("python", description="Linguagem origem"),
    ) -> str:
        """Converte codigo entre linguagens de programacao."""
        r = self._post(
            "/code_convert",
            {
                "codigo": codigo,
                "linguagem_origem": linguagem_origem,
                "linguagem_destino": linguagem_destino,
            },
        )
        return r.get("result", "sem resultado")

    # ============================================================
    # TESTES E DOCUMENTACAO
    # ============================================================

    def code_test(
        self,
        codigo: str = Field(..., description="Codigo a testar"),
        framework: str = Field(
            "pytest", description="Framework de teste (pytest, unittest)"
        ),
    ) -> str:
        """Cria testes unitarios para o codigo."""
        r = self._post("/code_test", {"codigo": codigo, "framework": framework})
        return r.get("result", "sem resultado")

    def code_document(
        self,
        codigo: str = Field(..., description="Codigo a documentar"),
        formato: str = Field(
            "google", description="Formato de docstring (google, numpy, sphinx)"
        ),
    ) -> str:
        """Adiciona docstrings e comentarios ao codigo sem alterar a logica."""
        r = self._post("/code_document", {"codigo": codigo, "formato": formato})
        return r.get("result", "sem resultado")

    # ============================================================
    # BONUS
    # ============================================================

    def code_diff(
        self,
        codigo_antigo: str = Field(..., description="Versao antiga do codigo"),
        codigo_novo: str = Field(..., description="Versao nova do codigo"),
    ) -> str:
        """Compara dois codigos e explica as diferencas entre eles."""
        r = self._post(
            "/code_diff", {"codigo_antigo": codigo_antigo, "codigo_novo": codigo_novo}
        )
        return r.get("result", "sem resultado")
