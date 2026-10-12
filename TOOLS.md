# MYRA Tools Reference

This document inventories public tools and bridge actions found in `tools/browseragent.py`, `tools/codeagent.py`, `tools/visuals_core.py`, `tasks/browser_bridge.py` and `tasks/structured_tools.py` on the documented repository revision. Tool registration/configuration may differ by runtime. Parameters marked optional have defaults in the source; verify the current signature before integrating.

## Navegador

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `open_url` | Abre uma URL no navegador Playwright. | `url: str` | `open_url(url="https://example.com")` |
| `search_google` | Pesquisa no Google. | `query: str` | `search_google(query="local AI agents")` |
| `search_in_page` | Procura texto na página atual. | `query: str` | `search_in_page(query="Pricing")` |
| `click_by_description` | Clica num link/botão pelo texto visível. | `text: str` | `click_by_description(text="Sign in")` |
| `type_text` | Preenche um campo identificado pelo placeholder. | `text: str, field_text: str` | `type_text(text="hello", field_text="Search")` |
| `press_key` | Pressiona uma tecla no navegador. | `key: str` | `press_key(key="Enter")` |
| `go_back` | Volta à página anterior. | Nenhum | `go_back()` |
| `wait` | Aguarda um número de segundos. | `seconds: float` | `wait(seconds=2)` |
| `read_page` | Lê texto e elementos clicáveis da página atual. | Nenhum | `read_page()` |
| `take_screenshot` | Captura screenshot da página atual. | Nenhum | `take_screenshot()` |
| `browser_get_tabs` | Lista separadores Chrome disponíveis pela bridge. | Nenhum | `browser_get_tabs()` |
| `browser_read_active_tab` | Lê conteúdo do separador ativo; pode filtrar pela URL. | `url_contains: str = ""` | `browser_read_active_tab(url_contains="github.com")` |
| `browser_read_page` | Lê conteúdo de uma URL HTTP/HTTPS permitida. | `url: str` | `browser_read_page(url="https://example.com")` |
| `browser_navigate_active_tab` | Navega o separador ativo para uma URL. | `url: str` | `browser_navigate_active_tab(url="https://example.com")` |
| `browser_new_tab` | Abre um separador novo. | `url: str` | `browser_new_tab(url="https://example.com")` |
| `browser_close_tab` | Fecha um separador, se indicado; caso contrário aplica o comportamento padrão da bridge. | `tab_id: int \| None = None` | `browser_close_tab(tab_id=123)` |
| `browser_type_text` | Digita texto num campo identificado por seletor CSS ou label. | `campo: str, texto: str` | `browser_type_text(campo="input[name=q]", texto="MYRA")` |
| `browser_click_text` | Clica num botão/link pelo texto. | `text: str` | `browser_click_text(text="Search")` |
| `browser_scroll` | Faz scroll na página. | `direcao: up/down/top/bottom = "down", quantidade: int = 500` | `browser_scroll(direcao="down", quantidade=600)` |
| `browser_wait` | Aguarda um período no browser bridge. | `ms: int` | `browser_wait(ms=1000)` |
| `browser_search_google` | Pesquisa usando a bridge sem depender da automação Playwright legada. | `termo: str` | `browser_search_google(termo="MYRA agent")` |
| `browser_search_google_visivel` | Pesquisa usando interação visível no Chrome. | `termo: str, delay_typing_ms: int = 150, scroll_suave: bool = False` | `browser_search_google_visivel(termo="MYRA", delay_typing_ms=150)` |
| `get_current_url` | Devolve a URL atual do navegador controlado. | Nenhum | `get_current_url()` |
| `read_page_structured` | Lê a página atual como dados estruturados. | Nenhum | `read_page_structured()` |

## Visão

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `see_image` | Analisa visualmente a tela atual usando o serviço de visão. | `pergunta: str = "Descreva em português..." ` | `see_image(pergunta="Onde está o botão de login?")` |
| `vision_locate` | Localiza um elemento visível por descrição e retorna coordenadas do centro. | `descricao: str` | `vision_locate(descricao="campo de pesquisa")` |
| `vision_click` | Localiza visualmente um elemento e clica no centro. | `descricao: str` | `vision_click(descricao="botão de login")` |
| `vision_type` | Localiza um campo visual, clica e digita texto. | `descricao: str, texto: str` | `vision_type(descricao="campo de email", texto="user@example.com")` |
| `pc_screenshot` | Captura a tela inteira do PC e guarda a imagem no diretório de screenshots configurado. | Nenhum | `pc_screenshot()` |

## Email

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `email_list` | Lista e-mails recentes da caixa de entrada. | `quantidade: int = 5` | `email_list(quantidade=10)` |
| `email_read` | Lê um e-mail pelo índice, 0 = mais recente. | `indice: int = 0` | `email_read(indice=0)` |
| `email_search` | Pesquisa por termo no assunto/corpo. | `termo: str, quantidade: int = 10` | `email_search(termo="interview", quantidade=5)` |
| `email_send` | Envia e-mail. | `para: str, assunto: str, corpo: str` | `email_send(para="a@example.com", assunto="Hello", corpo="Hi")` |
| `email_reply` | Responde ao e-mail identificado por índice. | `indice: int = 0, corpo: str` | `email_reply(indice=0, corpo="Obrigado pela mensagem.")` |
| `email_mark_read` | Marca como lido. | `indice: int = 0` | `email_mark_read(indice=0)` |
| `email_mark_unread` | Marca como não lido. | `indice: int = 0` | `email_mark_unread(indice=0)` |
| `email_move` | Move e-mail para pasta de destino. | `indice: int = 0, pasta_destino: str = "[Gmail]/Trash"` | `email_move(indice=0, pasta_destino="[Gmail]/Important")` |
| `email_delete_by_search` | Exclui até um limite de e-mails que correspondem ao termo. | `termo: str, limite: int = 10` | `email_delete_by_search(termo="Indeed", limite=5)` |

## Arquivos e utilitários

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `list_dir` | Lista arquivos e pastas. | `caminho: str = "."` | `list_dir(caminho="workspace")` |
| `read_file` | Lê um arquivo. | `caminho: str` | `read_file(caminho="workspace/notes.txt")` |
| `write_file` | Cria ou sobrescreve um arquivo. | `caminho: str, conteudo: str` | `write_file(caminho="workspace/a.txt", conteudo="Olá")` |
| `delete_file` | Exclui um arquivo. | `caminho: str` | `delete_file(caminho="workspace/tmp.txt")` |
| `create_dir` | Cria uma pasta. | `caminho: str` | `create_dir(caminho="workspace/reports")` |
| `move_file` | Move ou renomeia arquivo. | `origem: str, destino: str` | `move_file(origem="workspace/a.txt", destino="workspace/b.txt")` |
| `search_in_files` | Pesquisa texto nos arquivos por extensão. | `termo: str, extensao: str = ".txt"` | `search_in_files(termo="TODO", extensao=".py")` |
| `get_current_time` | Retorna data/hora atual. | Nenhum | `get_current_time()` |
| `save_note` | Guarda uma nota persistente. | `texto: str` | `save_note(texto="Rever a FASE 26")` |
| `read_notes` | Lê todas as notas guardadas. | Nenhum | `read_notes()` |
| `get_weather` | Obtém clima para a cidade indicada ou a cidade padrão. | `cidade: str = ""` | `get_weather(cidade="Dublin")` |
| `run_python` | Executa código Python. | `codigo: str` | `run_python(codigo="print(1 + 1)")` |
| `web_search` | Pesquisa na web via DuckDuckGo. | `query: str, max_resultados: int = 5` | `web_search(query="FastAPI docs", max_resultados=3)` |

## Automação PC

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `pc_move_mouse` | Move o cursor para coordenadas de ecrã. | `x: int, y: int` | `pc_move_mouse(x=800, y=450)` |
| `pc_click` | Clica na posição atual ou em coordenadas. | `x: int = None, y: int = None, button: str = "left"` | `pc_click(x=800, y=450, button="left")` |
| `pc_double_click` | Faz duplo clique. | `x: int = None, y: int = None` | `pc_double_click(x=800, y=450)` |
| `pc_right_click` | Faz clique direito. | `x: int = None, y: int = None` | `pc_right_click(x=800, y=450)` |
| `pc_type_text` | Digita texto na janela ativa. | `text: str` | `pc_type_text(text="Olá MYRA")` |
| `pc_press_key` | Pressiona uma tecla. | `key: str` | `pc_press_key(key="enter")` |
| `pc_hotkey` | Pressiona combinação de teclas. | `keys: list[str]` | `pc_hotkey(keys=["ctrl", "c"])` |
| `pc_scroll` | Rola a tela; sinal define a direção conforme a implementação. | `amount: int` | `pc_scroll(amount=-500)` |
| `pc_get_windows` | Lista títulos de janelas abertas. | Nenhum | `pc_get_windows()` |
| `pc_get_active_window` | Obtém título da janela em foco. | Nenhum | `pc_get_active_window()` |
| `pc_focus_window` | Traz para frente a janela pelo título parcial. | `titulo: str` | `pc_focus_window(titulo="Chrome")` |
| `pc_get_chats` | Lista chats recentes do MYRA. | `quantidade: int = 20` | `pc_get_chats(quantidade=5)` |
| `pc_remove_chat` | Exclui chat por índice. | `indice: int = 0` | `pc_remove_chat(indice=0)` |
| `pc_remove_chats_by_search` | Exclui chats cujo título contenha um termo. | `termo: str, limite: int = 20` | `pc_remove_chats_by_search(termo="Teste", limite=3)` |
| `pc_remove_all_chats` | Exclui todos os chats; exige confirmação explícita. | `confirmar: bool = False` | `pc_remove_all_chats(confirmar=True)` |
| `pc_rename_chat` | Renomeia chat por índice. | `indice: int = 0, novo_titulo: str` | `pc_rename_chat(indice=0, novo_titulo="Projeto MYRA")` |

## Código

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `code_generate` | Gera código a partir de uma descrição. | `descricao: str, linguagem: str = "python"` | `code_generate(descricao="API REST simples")` |
| `code_explain` | Explica código linha a linha. | `codigo: str` | `code_explain(codigo="print('hi')")` |
| `code_analyze` | Analisa bugs, segurança, performance e práticas. | `codigo: str` | `code_analyze(codigo="print('hi')")` |
| `code_review` | Faz revisão de código. | `codigo: str` | `code_review(codigo="def f(): pass")` |
| `code_refactor` | Refatora conforme um objetivo. | `codigo: str, objetivo: str` | `code_refactor(codigo="x=1", objetivo="melhorar legibilidade")` |
| `code_optimize` | Sugere/produz otimização mantendo comportamento. | `codigo: str` | `code_optimize(codigo="sum(range(100))")` |
| `code_convert` | Converte entre linguagens. | `codigo: str, linguagem_destino: str, linguagem_origem: str = "python"` | `code_convert(codigo="print(1)", linguagem_destino="javascript")` |
| `code_test` | Gera testes unitários. | `codigo: str, framework: str = "pytest"` | `code_test(codigo="def add(a,b): return a+b")` |
| `code_document` | Adiciona docstrings/comentários. | `codigo: str, formato: str = "google"` | `code_document(codigo="def add(a,b): return a+b")` |
| `code_diff` | Compara duas versões de código. | `codigo_antigo: str, codigo_novo: str` | `code_diff(codigo_antigo="x=1", codigo_novo="x=2")` |
| `code_sql` | Gera consulta SQL. | `descricao: str, dialeto: str = "postgresql"` | `code_sql(descricao="listar utilizadores", dialeto="sqlite")` |
| `code_regex` | Cria expressão regular a partir de descrição. | `descricao: str` | `code_regex(descricao="emails")` |
| `code_scaffold` | Cria estrutura inicial de projeto. | `tipo: str, nome: str = "meu_projeto"` | `code_scaffold(tipo="api fastapi", nome="myra_demo")` |
| `code_run` | Executa código Python e retorna saída/erro/código de saída. | `codigo: str` | `code_run(codigo="print(2 + 2)")` |
| `code_run_file` | Executa ficheiro Python em `workspace/code/`. | `caminho: str, args: list = []` | `code_run_file(caminho="main.py", args=[])` |
| `code_benchmark` | Mede tempo de execução repetido. | `codigo: str, repeticoes: int = 10` | `code_benchmark(codigo="sum(range(1000))", repeticoes=5)` |
| `code_dependencies` | Identifica dependências externas. | `codigo: str` | `code_dependencies(codigo="import requests")` |
| `code_snippet` | Gera pequeno snippet pronto a colar. | `descricao: str, linguagem: str = "python"` | `code_snippet(descricao="validar email")` |
| `code_readme` | Gera README a partir de código/projeto. | `codigo: str` | `code_readme(codigo="...")` |
| `code_metrics` | Mede linhas, comentários e caracteres. | `codigo: str` | `code_metrics(codigo="print(1)")` |
| `code_lint` | Verifica sintaxe Python com py_compile. | `codigo: str` | `code_lint(codigo="print('ok')")` |

## YouTube

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `youtube_search` | Pesquisa vídeos com yt-dlp. | `query: str, max_resultados: int = 5` | `youtube_search(query="AI agents", max_resultados=3)` |
| `youtube_channel_latest` | Obtém vídeos recentes de canal/handle/URL. | `channel: str, max_resultados: int = 3` | `youtube_channel_latest(channel="@OpenAI", max_resultados=3)` |
| `get_youtube_transcript` | Obtém transcrição, priorizando idiomas indicados. | `url: str, idiomas: list = ["en", "pt"]` | `get_youtube_transcript(url="https://youtube.com/watch?v=VIDEO_ID", idiomas=["pt", "en"])` |
| `get_youtube_summary` | Obtém transcrição e resume em português. | `url: str, max_pontos: int = 5` | `get_youtube_summary(url="https://youtube.com/watch?v=VIDEO_ID", max_pontos=5)` |

## Visualização

`tools/visuals_core.py` expõe ferramentas Open WebUI para renderização de dados. Os nomes abaixo são os métodos públicos identificados no código; confirme os parâmetros completos no schema do próprio Open WebUI antes de chamadas programáticas.

| Tool | Descrição | Parâmetros principais | Exemplo conceptual |
|---|---|---|---|
| `render_chart` | Gráfico de uma série (barra, linha ou dispersão), com saída embed/text/auto. | `x, y, title, chart_type, mode` | `render_chart(x=["Mon","Tue"], y=[2,5], title="Visitas", chart_type="line", mode="auto")` |
| `render_multi_chart` | Compara múltiplas séries. | Séries, título, tipo/modo conforme schema | Gráfico de visitas e conversões por dia. |
| `render_bar_chart` | Gráfico de barras ASCII/textual. | Dados e título conforme schema | Barras para vendas por mês. |
| `render_line_chart` | Gráfico de linhas ASCII/textual. | Dados e título conforme schema | Linha de evolução semanal. |
| `render_table` | Tabela de dados. | `columns, rows, title, mode` | Tabela de tarefas e estados. |
| `render_comparison_table` | Tabela comparativa e identificação de melhores valores. | Linhas/colunas e configuração conforme schema | Comparar três modelos locais. |
| `render_heatmap` | Mapa de calor de uma matriz. | Matriz/dados, rótulos e título conforme schema | Heatmap de erros por dia. |
| `render_timeline` | Linha temporal. | Eventos/dados temporais conforme schema | Cronologia de commits. |
| `render_flowchart` | Fluxograma. | Nós/arestas ou descrição estruturada conforme schema | Fluxo de execução da MYRA. |
| `render_tree` | Árvore hierárquica. | Estrutura em árvore ou arestas conforme schema | Árvore de pastas. |

## Ferramentas estruturadas de pesquisa

Estas funções estão em `tasks/structured_tools.py` e são registadas no planner:

| Tool | Descrição | Parâmetros | Exemplo |
|---|---|---|---|
| `search_google_structured` | Pesquisa Google e devolve resultados estruturados. | `query: str, max_resultados: int = 5` | `search_google_structured(query="FastAPI", max_resultados=3)` |
| `web_search_structured` | Pesquisa DuckDuckGo com resultados estruturados. | `query: str, max_resultados: int = 5` | `web_search_structured(query="local AI", max_resultados=3)` |
| `youtube_search` | Pesquisa vídeos do YouTube. | `query: str, max_resultados: int = 5` | `youtube_search(query="MYRA AI")` |
| `youtube_channel_latest` | Obtém vídeos recentes de um canal. | `channel: str, max_resultados: int = 3` | `youtube_channel_latest(channel="@OpenAI")` |
| `get_current_url` | Retorna a URL atual do navegador. | Nenhum | `get_current_url()` |
| `read_page_structured` | Retorna conteúdo da página em JSON estruturado. | Nenhum | `read_page_structured()` |

## API do Browser Bridge (integração, não ferramentas de usuário)

- `browser_bridge_next`: entrega à extensão o próximo comando da fila; recebe token `X-MYRA-BRIDGE-TOKEN` e parâmetros de espera/long-poll.
- `browser_bridge_complete`: recebe `command_id` e o resultado da extensão, com o mesmo token.
- A bridge permite somente as ações listadas na allowlist do código: `read_active_tab`, `read_page_url`, `navigate_active_tab`, `click_text`, `get_tabs`, `type_text`, `new_tab`, `close_tab`, `scroll`, `search_google`, `search_google_visivel`.
- Os parâmetros são validados (URLs HTTP/HTTPS, tamanho de texto, termos de pesquisa, direções/quantidade de scroll e IDs de separador). A bridge persiste comandos/resultados em SQLite local.
- Exemplo de fluxo: o planner chama `browser_click_text(text="Settings")`; a bridge grava o comando, a extensão executa e devolve o resultado; o planner recebe o resultado estruturado.

## Observações de segurança

- Envio/exclusão de e-mail e exclusão de chats são ações com consequências reais; confirmar os argumentos e a intenção do utilizador.
- `code_run`, `code_run_file` e `run_python` executam código: limitar o workspace e rever código não confiável.
- O bridge deve permanecer local e o token não deve ser commitado nem partilhado.
- Esta documentação descreve ferramentas identificadas no código-fonte; a disponibilidade depende do registo e configuração em runtime.
