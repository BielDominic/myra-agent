import requests
from pydantic import BaseModel, Field


class Tools:
    def __init__(self):
        self.base_url = "http://host.docker.internal:8000"

    def _post(self, rota: str, payload: dict) -> dict:
        try:
            r = requests.post(f"{self.base_url}{rota}", json=payload, timeout=300)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            return {"status": "erro", "result": "agent.py inacessivel"}
        except Exception as e:
            return {"status": "erro", "result": f"Erro: {type(e).__name__}"}

    # ============================================================
    # NAVEGADOR
    # ============================================================

    def open_url(
        self,
        url: str = Field(..., description="URL completa. Ex: https://www.google.com"),
    ) -> str:
        """Abre uma URL no navegador."""
        r = self._post("/open_url", {"url": url})
        return r.get("result", "sem resultado")

    def search_google(
        self,
        query: str = Field(..., description="Termo de busca no Google"),
    ) -> str:
        """Pesquisa NO GOOGLE."""
        r = self._post("/search_google", {"query": query})
        return r.get("result", "sem resultado")

    def search_in_page(
        self,
        query: str = Field(..., description="Texto a pesquisar na pagina atual"),
    ) -> str:
        """Pesquisa na PAGINA ATUAL."""
        r = self._post("/search_in_page", {"query": query})
        return r.get("result", "sem resultado")

    def click_by_description(
        self,
        text: str = Field(..., description="Descricao do que clicar"),
    ) -> str:
        """Clica em um link/botao pelo texto visivel."""
        r = self._post("/click_by_description", {"text": text})
        return r.get("result", "sem resultado")

    def type_text(
        self,
        text: str = Field(..., description="Texto a digitar"),
        field_text: str = Field(..., description="Placeholder do campo"),
    ) -> str:
        """Digita em um campo."""
        r = self._post("/type_text", {"text": text, "field_text": field_text})
        return r.get("result", "sem resultado")

    def press_key(
        self,
        key: str = Field(..., description="Tecla. Ex: Enter"),
    ) -> str:
        """Pressiona uma tecla."""
        r = self._post("/press_key", {"key": key})
        return r.get("result", "sem resultado")

    def go_back(self) -> str:
        """Volta para a pagina anterior."""
        r = self._post("/go_back", {})
        return r.get("result", "sem resultado")

    def wait(
        self, seconds: float = Field(..., description="Segundos para esperar")
    ) -> str:
        """Espera N segundos."""
        r = self._post("/wait", {"seconds": seconds})
        return r.get("result", "sem resultado")

    def read_page(self) -> str:
        """Le a pagina atual."""
        r = self._post("/read_page", {})
        texto = r.get("result", "")
        clicaveis = r.get("clicaveis", [])
        return f"TEXTO:\n{texto}\n\nCLICAVEIS:\n" + "\n".join(clicaveis)

    # ============================================================
    # VISAO
    # ============================================================

    def take_screenshot(self) -> str:
        """Tira um print da pagina atual."""
        r = self._post("/screenshot", {})
        return r.get("result", "sem resultado")

    def see_image(
        self,
        pergunta: str = "Descreva em portugues o que voce ve nesta tela, em 2 frases.",
    ) -> str:
        """Analisa a tela atual usando visao."""
        r = self._post("/see", {"pergunta": pergunta})
        return r.get("result", "sem resultado")

    # ============================================================
    # EMAIL (IMAP/SMTP)
    # ============================================================

    def email_list(self, quantidade: int = 5) -> str:
        """Lista os ultimos emails da caixa de entrada do Gmail."""
        r = self._post("/email_list", {"quantidade": quantidade})
        return r.get("result", "sem resultado")

    def email_read(self, indice: int = 0) -> str:
        """Le um email especifico pelo indice (0 = mais recente)."""
        r = self._post("/email_read", {"indice": indice})
        return r.get("result", "sem resultado")

    def email_search(
        self,
        termo: str = Field(..., description="Termo a buscar no assunto ou corpo"),
        quantidade: int = 10,
    ) -> str:
        """Busca emails por termo."""
        r = self._post(
            "/email_search",
            {"termo": termo, "pasta": "INBOX", "quantidade": quantidade},
        )
        return r.get("result", "sem resultado")

    def email_mark_read(self, indice: int = 0) -> str:
        """Marca um email como LIDO."""
        r = self._post("/email_mark_read", {"indice": indice, "pasta": "INBOX"})
        return r.get("result", "sem resultado")

    def email_mark_unread(self, indice: int = 0) -> str:
        """Marca um email como NAO LIDO."""
        r = self._post("/email_mark_unread", {"indice": indice, "pasta": "INBOX"})
        return r.get("result", "sem resultado")

    def email_move(
        self,
        indice: int = 0,
        pasta_destino: str = "[Gmail]/Trash",
    ) -> str:
        """Move um email para outra pasta."""
        r = self._post(
            "/email_move",
            {
                "indice": indice,
                "pasta_origem": "INBOX",
                "pasta_destino": pasta_destino,
            },
        )
        return r.get("result", "sem resultado")

    def email_delete_by_search(
        self,
        termo: str = Field(
            ...,
            description="Termo a buscar no assunto ou corpo. Ex: 'LinkedIn', 'Indeed'",
        ),
        limite: int = Field(
            10, description="Quantidade maxima de emails a apagar (padrao: 10)"
        ),
    ) -> str:
        """Apaga emails que contem o termo (LinkedIn, Indeed, etc.).
        Use quando o usuario pedir para apagar emails de um remetente/assunto.
        Ex: 'Apague 5 emails do LinkedIn' -> use termo='LinkedIn' e limite=5.
        Se o usuario nao especificar a quantidade, use o padrao (10)."""
        r = self._post(
            "/email_delete_by_search",
            {"termo": termo, "pasta": "INBOX", "limite": limite},
        )
        return r.get("result", "sem resultado")

    def email_send(
        self,
        para: str = Field(..., description="Email do destinatario"),
        assunto: str = Field(..., description="Assunto do email"),
        corpo: str = Field(..., description="Corpo do email"),
    ) -> str:
        """Envia um email."""
        r = self._post(
            "/email_send", {"para": para, "assunto": assunto, "corpo": corpo}
        )
        return r.get("result", "sem resultado")

    def email_reply(
        self,
        indice: int = 0,
        corpo: str = Field(..., description="Corpo da resposta"),
    ) -> str:
        """Responde um email."""
        r = self._post(
            "/email_reply", {"indice": indice, "pasta": "INBOX", "corpo": corpo}
        )
        return r.get("result", "sem resultado")

    # ============================================================
    # UTILITARIAS
    # ============================================================

    def get_current_time(self) -> str:
        """Retorna a data e hora atual."""
        r = self._post("/get_current_time", {})
        return r.get("result", "sem resultado")

    def save_note(self, texto: str = Field(..., description="Texto da nota")) -> str:
        """Salva uma nota."""
        r = self._post("/save_note", {"texto": texto})
        return r.get("result", "sem resultado")

    def read_notes(self) -> str:
        """Le todas as notas."""
        r = self._post("/read_notes", {})
        return r.get("result", "sem resultado")

    def get_weather(self, cidade: str = "") -> str:
        """Retorna o clima da cidade. Se cidade vazia, usa a cidade padrao configurada."""
        r = self._post("/get_weather", {"cidade": cidade})
        return r.get("result", "sem resultado")

    def run_python(self, codigo: str = Field(..., description="Codigo Python")) -> str:
        """Executa codigo Python."""
        r = self._post("/run_python", {"codigo": codigo})
        return r.get("result", "sem resultado")

    # ============================================================
    # ARQUIVOS
    # ============================================================

    def list_dir(self, caminho: str = ".") -> str:
        """Lista arquivos/pastas."""
        r = self._post("/list_dir", {"caminho": caminho})
        return r.get("result", "sem resultado")

    def read_file(self, caminho: str = Field(..., description="Caminho")) -> str:
        """Le um arquivo."""
        r = self._post("/read_file", {"caminho": caminho})
        return r.get("result", "sem resultado")

    def write_file(
        self,
        caminho: str = Field(..., description="Caminho"),
        conteudo: str = Field(..., description="Conteudo"),
    ) -> str:
        """Cria/sobrescreve um arquivo."""
        r = self._post("/write_file", {"caminho": caminho, "conteudo": conteudo})
        return r.get("result", "sem resultado")

    def delete_file(self, caminho: str = Field(..., description="Caminho")) -> str:
        """Apaga um arquivo."""
        r = self._post("/delete_file", {"caminho": caminho})
        return r.get("result", "sem resultado")

    def create_dir(self, caminho: str = Field(..., description="Caminho")) -> str:
        """Cria uma pasta."""
        r = self._post("/create_dir", {"caminho": caminho})
        return r.get("result", "sem resultado")

    def move_file(
        self,
        origem: str = Field(..., description="Caminho de origem"),
        destino: str = Field(..., description="Caminho de destino"),
    ) -> str:
        """Move/renomeia um arquivo."""
        r = self._post("/move_file", {"origem": origem, "destino": destino})
        return r.get("result", "sem resultado")

    def search_in_files(
        self,
        termo: str = Field(..., description="Texto a buscar"),
        extensao: str = ".txt",
    ) -> str:
        """Busca texto nos arquivos."""
        r = self._post("/search_in_files", {"termo": termo, "extensao": extensao})
        return r.get("result", "sem resultado")

    # ============================================================
    # WEB SEARCH
    # ============================================================

    def web_search(
        self,
        query: str = Field(..., description="Termo de busca"),
        max_resultados: int = 5,
    ) -> str:
        """Pesquisa na web via DuckDuckGo."""
        r = self._post(
            "/web_search", {"query": query, "max_resultados": max_resultados}
        )
        return r.get("result", "sem resultado")

    # ============================================================
    # AUTOMACAO DO PC (FASE 16) - mouse, teclado, tela, janelas
    # ============================================================

    def pc_move_mouse(
        self,
        x: int = Field(..., description="Coordenada X na tela (pixels)"),
        y: int = Field(..., description="Coordenada Y na tela (pixels)"),
    ) -> str:
        """Move o mouse do computador para a posicao (x, y) na tela.
        Use quando o usuario pedir para mover o mouse, posicionar o cursor
        ou clicar em coordenadas especificas."""
        r = self._post("/pc_move_mouse", {"x": x, "y": y})
        return r.get("result", "sem resultado")

    def pc_click(
        self,
        x: int = Field(None, description="Coordenada X (opcional)"),
        y: int = Field(None, description="Coordenada Y (opcional)"),
        button: str = Field("left", description="Botao: 'left', 'right' ou 'middle'"),
    ) -> str:
        """Clica no computador. Se x e y forem passados, move antes de clicar;
        caso contrario, clica na posicao atual do mouse."""
        payload = {"button": button}
        if x is not None:
            payload["x"] = x
        if y is not None:
            payload["y"] = y
        r = self._post("/pc_click", payload)
        return r.get("result", "sem resultado")

    def pc_double_click(
        self,
        x: int = Field(None, description="Coordenada X (opcional)"),
        y: int = Field(None, description="Coordenada Y (opcional)"),
    ) -> str:
        """Da um duplo clique no computador. Se x e y forem passados, move antes."""
        payload = {}
        if x is not None:
            payload["x"] = x
        if y is not None:
            payload["y"] = y
        r = self._post("/pc_double_click", payload)
        return r.get("result", "sem resultado")

    def pc_right_click(
        self,
        x: int = Field(None, description="Coordenada X (opcional)"),
        y: int = Field(None, description="Coordenada Y (opcional)"),
    ) -> str:
        """Da um clique direito no computador. Se x e y forem passados, move antes."""
        payload = {}
        if x is not None:
            payload["x"] = x
        if y is not None:
            payload["y"] = y
        r = self._post("/pc_right_click", payload)
        return r.get("result", "sem resultado")

    def pc_type_text(
        self,
        text: str = Field(..., description="Texto a digitar no teclado do PC"),
    ) -> str:
        """Digita texto usando o teclado do computador (na janela ativa).
        Use quando o usuario pedir para digitar em algum programa do PC."""
        r = self._post("/pc_type_text", {"text": text})
        return r.get("result", "sem resultado")

    def pc_press_key(
        self,
        key: str = Field(
            ...,
            description="Tecla a pressionar. Ex: 'enter', 'tab', 'esc', 'f5', 'win'",
        ),
    ) -> str:
        """Pressiona uma tecla no teclado do PC."""
        r = self._post("/pc_press_key", {"key": key})
        return r.get("result", "sem resultado")

    def pc_hotkey(
        self,
        keys: list = Field(
            ...,
            description="Lista de teclas para combinar. Ex: ['ctrl','c'], ['alt','tab'], ['win','d']",
        ),
    ) -> str:
        """Pressiona uma combinacao de teclas no PC (ex: Ctrl+C, Alt+Tab, Win+D)."""
        r = self._post("/pc_hotkey", {"keys": keys})
        return r.get("result", "sem resultado")

    def pc_scroll(
        self,
        amount: int = Field(
            ...,
            description="Quantidade de scroll. Positivo = cima, negativo = baixo",
        ),
    ) -> str:
        """Rola a tela do PC para cima ou para baixo."""
        r = self._post("/pc_scroll", {"amount": amount})
        return r.get("result", "sem resultado")

    def pc_screenshot(self) -> str:
        """Tira um screenshot da TELA DO PC (nao do navegador) e salva em
        C:\\computer-agent\\screenshots. Use quando o usuario pedir para
        capturar o que esta vendo no computador."""
        r = self._post("/pc_screenshot", {"salvar": True})
        return r.get("result", "sem resultado")

    def pc_get_windows(self) -> str:
        """Lista todas as janelas abertas no PC (titulos).
        Use quando o usuario perguntar quais programas/janelas estao abertos."""
        r = self._post("/pc_get_windows", {})
        result = r.get("result", [])
        if isinstance(result, list):
            return "\n".join(result) if result else "(nenhuma janela aberta)"
        return str(result)

    def pc_get_active_window(self) -> str:
        """Retorna o titulo da janela ativa no PC (a que esta em foco agora)."""
        r = self._post("/pc_get_active_window", {})
        return r.get("result", "sem resultado")

    def pc_focus_window(
        self,
        titulo: str = Field(
            ...,
            description="Titulo (ou parte) da janela. Ex: 'Chrome', 'Notepad'",
        ),
    ) -> str:
        """Foca uma janela do PC pelo titulo. Use quando o usuario pedir
        para trazer algum programa para frente."""
        r = self._post("/pc_focus_window", {"titulo": titulo})
        return r.get("result", "sem resultado")

    # ============================================================
    # GERENCIAMENTO DE CHATS (FASE 10) - nomes pc_get_* / pc_remove_*
    # ============================================================

    def pc_get_chats(
        self,
        quantidade: int = Field(20, description="Quantos chats listar (padrao: 20)"),
    ) -> str:
        """Lista os ultimos N chats do MYRA (mais recentes primeiro).
        Use quando o usuario pedir para listar seus chats."""
        r = self._post("/pc_get_chats", {"quantidade": quantidade})
        result = r.get("result", [])
        if isinstance(result, list):
            return "\n".join(result) if result else "(nenhum chat)"
        return str(result)

    def pc_remove_chat(
        self,
        indice: int = Field(0, description="Indice do chat (0 = mais recente)"),
    ) -> str:
        """Apaga 1 chat especifico pelo indice.
        Use quando o usuario pedir para apagar um chat especifico pelo numero."""
        r = self._post("/pc_remove_chat", {"indice": indice})
        return r.get("result", "sem resultado")

    def pc_remove_chats_by_search(
        self,
        termo: str = Field(..., description="Termo a buscar no titulo dos chats"),
        limite: int = Field(20, description="Numero maximo de chats a apagar"),
    ) -> str:
        """Apaga TODOS os chats cujo titulo contenha o termo.
        Use quando o usuario pedir para apagar chats com um termo no titulo.
        Ex: 'Apague os chats com Teste no titulo' -> termo='Teste'.
        Ex: 'Apague todos os chats sobre email' -> termo='email'."""
        r = self._post("/pc_remove_chats_by_search", {"termo": termo, "limite": limite})
        return r.get("result", "sem resultado")

    def pc_remove_all_chats(
        self,
        confirmar: bool = Field(
            False,
            description="Precisa ser True para confirmar. NAO passe True a menos que o usuario tenha pedido EXPLICITAMENTE para apagar TODOS os chats.",
        ),
    ) -> str:
        """Apaga TODOS os chats do usuario. ACAO DESTRUTIVA.
        Se o usuario pedir 'apague todos os meus chats', chame com confirmar=True."""
        r = self._post("/pc_remove_all_chats", {"confirmar": confirmar})
        return r.get("result", "sem resultado")

    def pc_rename_chat(
        self,
        indice: int = Field(0, description="Indice do chat (0 = mais recente)"),
        novo_titulo: str = Field(..., description="Novo titulo do chat"),
    ) -> str:
        """Renomeia um chat especifico pelo indice.
        Use quando o usuario pedir para renomear um chat.
        Ex: 'Renomeie o chat 0 para Projeto X' -> indice=0, novo_titulo='Projeto X'."""
        r = self._post(
            "/pc_rename_chat", {"indice": indice, "novo_titulo": novo_titulo}
        )
        return r.get("result", "sem resultado")

    # ============================================================
    # YOUTUBE (FASE 20)
    # ============================================================

    def get_youtube_transcript(
        self,
        url: str = Field(
            ...,
            description="URL completa do YouTube (youtube.com/watch?v=... ou youtu.be/...) ou o ID do video (11 caracteres).",
        ),
        idiomas: list = Field(
            ["en", "pt"],
            description="Lista de idiomas em ordem de prioridade. Padrao: ingles, portugues.",
        ),
    ) -> str:
        """Baixa a transcricao completa de um video do YouTube.
        Use quando o usuario pedir para pegar a transcricao de um video."""
        r = self._post("/youtube_transcript", {"url": url, "idiomas": idiomas})
        return r.get("result", "sem resultado")

    def get_youtube_summary(
        self,
        url: str = Field(
            ...,
            description="URL do video do YouTube a resumir.",
        ),
        max_pontos: int = Field(
            5,
            description="Numero maximo de pontos no resumo (padrao: 5).",
        ),
    ) -> str:
        """Baixa a transcricao de um video do YouTube E retorna um resumo em portugues.
        Use quando o usuario pedir para RESUMIR, ANALISAR, EXPLICAR ou fazer PERGUNTAS sobre um video.
        Retorna o resumo JA PRONTO (curto, otimo para mostrar direto)."""
        r = self._post("/youtube_summarize", {"url": url, "max_pontos": max_pontos})
        return r.get("result", "sem resultado")

    # ============================================================
    # TASK RUN (FASE 22-light) - agente autonomo simples
    # ============================================================

    def task_run(
        self,
        objetivo: str = Field(
            ...,
            description=(
                "O que deve ser feito, em linguagem natural. "
                "Ex: 'pesquise os melhores cursos de IA em Dublin e diga 3 nomes', "
                "'que horas sao agora?', 'resuma o video https://youtube.com/watch?v=...'"
            ),
        ),
        max_passos: int = Field(
            5,
            description="Limite de passos do plano (padrao: 5). Aumente para tarefas mais complexas.",
        ),
    ) -> str:
        """Executa uma tarefa COMPLETA de forma autonoma: planeja os passos,
        escolhe as ferramentas certas, executa cada passo, e sintetiza a resposta final.

        Use quando o usuario pedir para VOCE RESOLVER algo de ponta a ponta,
        sem precisar chamar ferramenta por ferramenta.

        Exemplos:
        - "pesquise X e me diga Y"
        - "veja o tempo em Dublin e me avise se devo levar guarda-chuva"
        - "resuma esse video do YouTube"

        Para tarefas simples de 1 passo (ex: "que horas sao"), prefira chamar
        a ferramenta especifica direto (get_current_time). Use task_run quando
        o objetivo envolver 2+ etapas ou quando o usuario pedir algo mais elaborado.
        """
        r = self._post(
            "/task_simple",
            {"objetivo": objetivo, "max_passos": max_passos},
        )

        if r.get("status") == "erro":
            erro = r.get("erro") or r.get("result") or "erro desconhecido"
            return f"ERRO ao executar task: {erro}"

        plano = r.get("plano", [])
        if plano:
            ferramentas = " -> ".join(p.get("ferramenta", "?") for p in plano)
        else:
            ferramentas = "(plano vazio)"

        resultado = r.get("resultado_final") or "(sem resultado)"

        return (
            f"**Plano executado:** {ferramentas}\n\n"
            f"**Resultado:**\n{resultado}"
        )