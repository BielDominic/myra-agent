# Computer Agent

Agente de navegador local controlado por linguagem natural, integrado ao Open WebUI.

## Arquitetura

Usuario -> Open WebUI (Docker, 3000) -> LLM local (Ollama, qwen2.5:3b) -> Tool BrowserAgent -> agent.py (FastAPI, 8000) -> Playwright -> Chromium -> Internet

## Acoes disponiveis (rotas do agent.py)

| Rota | Acao |
|---|---|
| POST /open_url | Abre uma URL |
| POST /search_google | Pesquisa no Google |
| POST /click_element | Clica por texto ou seletor CSS |
| POST /click_by_description | Clica por descricao (fallback pro primeiro link) |
| POST /type_text | Digita em um campo |
| POST /press_key | Pressiona uma tecla |
| POST /go_back | Volta uma pagina |
| POST /wait | Espera N segundos |
| POST /read_page | Le texto + lista de elementos clicaveis |

## Estrutura de arquivos

C:\computer-agent\
- agent.py              # Servidor FastAPI + Playwright
- start.ps1             # Script de inicializacao
- status.ps1            # Script de verificacao
- README.md             # Este arquivo
- venv\                 # Ambiente virtual Python
- agent_backup_v1.py    # Backup

## Como iniciar

### Inicio rapido

Abra o PowerShell em C:\computer-agent e rode:

    .\start.ps1

### Inicio manual

Janela 1 - Uvicorn:

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    uvicorn agent:app --host 127.0.0.1 --port 8000

Janela 2 - Ollama (background):

    $env:OLLAMA_LLM_LIBRARY="cuda_v12"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

Janela 3 - Docker Desktop deve estar aberto.

## Como usar

1. Abra http://localhost:3000
2. New Chat
3. Selecione o modelo Local Agent
4. Digite comandos em portugues

### Exemplos

- Abra o Google
- Pesquise por Open WebUI
- Abra https://example.com
- Clique no link
- Clique em Learn more
- Volte
- Leia a pagina
- Espere 3 segundos
- Pressione Enter

## Configuracao critica

### Ollama precisa de CUDA v12

A placa RTX A2000 do notebook tem problema com CUDA v13 (crash 0xc0000409). Sempre inicie o Ollama com:

    $env:OLLAMA_LLM_LIBRARY="cuda_v12"

### Variavel de ambiente permanente (recomendado)

1. Win + R -> sysdm.cpl -> Enter
2. Aba Avancado -> Variaveis de Ambiente
3. Variaveis do usuario -> Novo
4. Nome: OLLAMA_LLM_LIBRARY
5. Valor: cuda_v12

### Open WebUI (Docker)

- URL do Ollama no Open WebUI: http://host.docker.internal:11434
- URL do agent.py na Tool: http://host.docker.internal:8000

## Solucao de problemas

### Os modelos sumiram do Open WebUI

O Ollama foi reiniciado e o Open WebUI nao percebeu.
1. Admin Settings -> Connections
2. Clique no refresh (ou Save) ao lado do Ollama API
3. Recarregue a pagina (F5)

### agent.py inacessivel

O Uvicorn caiu. Reinicie:

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    uvicorn agent:app --host 127.0.0.1 --port 8000

### O clique nao funciona

O click_by_description tem 4 camadas:
1. Tenta o texto exato
2. Tenta por role (link/button)
3. Fallback: clica no primeiro link da pagina
4. Retorna a lista de clicaveis

### CUDA error: shared object initialization failed

Voce esqueceu OLLAMA_LLM_LIBRARY=cuda_v12.

### Chromium nao abre

Feche todos os Chromium abertos. O agent.py detecta e recria o browser.

## Modelos instalados

- qwen2.5:3b (usado pelo Local Agent - 1.9 GB)
- llama3.1:8b (4.9 GB - nao cabe na GPU de 4 GB)
- R4C3R/qwen2.5-coder-3b-heretic (6.2 GB)
- refinedneuro/refinedtoolcallv5-3b (2.5 GB)
- goekdenizguelmez/JOSIE:4b-instruct-q4_k_m (2.5 GB)
- gemma2:2b (1.6 GB)

## Limitacoes

1. Modelos 3B tem dificuldade com multi-step. Por isso o click_by_description faz o trabalho pesado.
2. A GPU RTX A2000 Laptop tem 4 GB dedicados. Modelos > 4 GB vao para CPU (lento).
3. Cada acao e uma mensagem separada (loop SEE->THINK->ACT ainda nao implementado).
4. Sem confirmacao antes de acoes irreversiveis.

## Proximas fases

- FASE 4: Loop SEE -> THINK -> ACT
- FASE 5: Screenshots + visao
- FASE 7: Agente autonomo
- FASE 8: Confirmacao antes de acoes criticas

## Historico

Construido em 23/09/2026. A grande virada foi o click_by_description com fallback, que compensa a limitacao do LLM pequeno.

## Anti-deteccao e fallback de busca

O agent.py tem 3 camadas de protecao:

1. Perfil persistente (cookies, sessao): C:\computer-agent\chromium_profile
   - Tudo que voce faz no Chromium fica salvo entre execucoes
   - Se o Google pedir CAPTCHA uma vez e voce resolver, nao pede de novo

2. Anti-deteccao:
   - navigator.webdriver escondido
   - User-Agent real do Chrome 131
   - --disable-blink-features=AutomationControlled

3. Fallback automatico para DuckDuckGo:
   - Se o Google bloquear, o agent.py detecta e cai no DuckDuckGo sozinho
   - Testa 6 seletores diferentes para achar o campo de busca
   - O agente NUNCA fica travado por causa de CAPTCHA

## Como usar o perfil persistente

Para "ensinar" o agente a passar pelo Google:

1. Mande "Abra https://www.google.com" no chat
2. Quando o Chromium abrir, resolva o CAPTCHA manualmente
3. Aceite os cookies
4. Feche o Chromium (o perfil salva tudo)
5. Na proxima vez, o Google lembra de voce

## Auto-recuperacao do Chrome

O start_browser() foi feito para se recuperar automaticamente de:

1. Chrome fechado manualmente
2. Chrome travado
3. Contexto do Playwright morto
4. Lock file do perfil travado

Fluxo de recuperacao:

1. _contexto_vivo() tenta page.title() - se falhar, contexto morreu
2. Fecha context/browser/playwright antigos (ignora erros)
3. Remove SingletonLock, SingletonCookie, SingletonSocket do perfil
4. Cria novo Chrome com launch_persistent_context
5. Aplica scripts anti-deteccao
6. Retorna a nova page

Consequencia: voce NUNCA precisa reiniciar o Uvicorn por causa de Chrome fechado.
Basta mandar o proximo comando e ele reabre o Chrome sozinho.

## search_in_page - busca contextual

O agent.py tem DUAS rotas de pesquisa:

- search_google(query): pesquisa NO GOOGLE (so use quando NAO especificar o site)
- search_in_page(query): pesquisa NA PAGINA ATUAL (YouTube, Wikipedia, LinkedIn, etc)

O search_in_page testa 8 seletores diferentes para achar a barra de pesquisa.

## type_text compativel com React

O type_text detecta automaticamente:

- Campo de SENHA: input[type='password']
- Campo de EMAIL/USUARIO: input[type='email'] ou input[type='text']
- Usa press_sequentially em vez de fill (React aceita)

## Modelo recomendado: llama3.1:8b

O LLM do chat DEVE ter a capacidade "tools". Sem isso, ele NARRA as acoes em vez de executa-las.

Modelos testados:

| Modelo | Tem tools? | Funciona? |
|---|---|---|
| llama3.1:8b | SIM | Funciona perfeitamente |
| qwen2.5:3b | SIM | As vezes narra (pequeno) |
| qwen2.5-coder-3b-heretic | SIM | Narra muito (foco em codigo) |
| dolphin-llama3:8b | NAO | So completion, nao serve |
| gemma2:2b | NAO | Nao serve |

Configuracao do Local Agent:

- Base Model: llama3.1:8b
- Function Calling: Native
- max_tokens: 2048
- num_ctx (Ollama): 8192
- Tool BrowserAgent marcada

Por que num_ctx=8192 e obrigatorio:
- Com 4096, as definicoes das 10 ferramentas nao cabem
- O Ollama trunca, o LLM perde as definicoes, e ele NARRA em vez de chamar
- Com 8192, tudo cabe e o tool calling funciona

Performance:
- ~12 segundos por resposta (com offload GPU+CPU)
- A RTX A2000 tem 4 GB de VRAM dedicada

## Email via IMAP/SMTP

O agente tem 3 rotas de email que NAO passam pelo navegador (o Google bloqueia login por automacao):

- email_list(quantidade): lista os ultimos emails da caixa de entrada
- email_read(indice): le um email pelo indice (0 = mais recente)
- email_send(para, assunto, corpo): envia email (usa SMTP)

Configuracao necessaria:
1. Ativar 2FA na conta Google
2. Gerar senha de app em https://myaccount.google.com/apppasswords
3. Definir variaveis de ambiente:
   [System.Environment]::SetEnvironmentVariable("GMAIL_USER", "seuemail@gmail.com", "User")
   [System.Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", "senha16caracteres", "User")

O Uvicorn precisa ser iniciado com essas variaveis:
   $env:GMAIL_USER = [System.Environment]::GetEnvironmentVariable('GMAIL_USER', 'User')
   $env:GMAIL_APP_PASSWORD = [System.Environment]::GetEnvironmentVariable('GMAIL_APP_PASSWORD', 'User')
   uvicorn agent:app --host 127.0.0.1 --port 8000

## Nota sobre Google

O Google (Gmail, Google Drive) BLOQUEIA login via automacao (Playwright). Mesmo com perfil dedicado,
anti-deteccao e cookies corretos, o Google recusa com "Couldn't sign you in".

Solucao: usar IMAP/SMTP para Gmail. Funciona 100% e nao passa pelo navegador.

## Nota sobre o modelo

O llama3.1:8b funciona em tool calling, MAS as vezes "narra" em vez de chamar (especialmente
em chats com historico longo). Sempre use CHAT NOVO para tarefas criticas.

Se continuar narrando, considere trocar para qwen2.5:7b.

## FASE B - Arquivos

O agente tem 3 ferramentas de arquivo:
- list_dir(caminho) - lista arquivos/pastas
- read_file(caminho) - le um arquivo
- write_file(caminho, conteudo) - cria/sobrescreve arquivo

Todas as operacoes sao RESTRITAS ao workspace: C:\computer-agent\workspace
O agente NAO pode acessar arquivos fora dessa pasta (seguranca).

## Estado atual (24/09/2026)

O agente tem 21 rotas no agent.py:
- 10 de navegador (open_url, search_google, search_in_page, click_element, click_by_description, type_text, press_key, go_back, wait, read_page)
- 3 de email (email_list, email_read, email_send) - via IMAP/SMTP
- 5 utilitarias (get_current_time, save_note, read_notes, get_weather, run_python)
- 3 de arquivo (list_dir, read_file, write_file)
- 1 de confirmacao (request_confirmation)

## Proximos passos

- FASE B2: agent-search (busca real na web sem API)
- FASE C: mais ferramentas de arquivo (delete_file, create_dir, etc)
- FASE D: automacao do PC (run_command com confirmacao)

## DESCOBERTA IMPORTANTE: modelo qwen2.5:7b

O modelo llama3.1:8b NAO funciona bem com muitas ferramentas (21 no total).
Ele entra em "modo narrador" - escreve o nome da ferramenta em texto em vez de chamar.

O modelo qwen2.5:7b funciona PERFEITAMENTE. Ele foi treinado para tool calling.
Use SEMPRE qwen2.5:7b como Base Model do Local Agent.

Configuracao do Local Agent:
- Base Model: qwen2.5:7b
- Function Calling: Native
- max_tokens: 2048
- num_ctx (Ollama): 8192
- Tool: BrowserAgent marcada

## Estado atual (24/09/2026)

O agente tem 21 rotas no agent.py:

NAVEGADOR (10):
open_url, search_google, search_in_page, click_element,
click_by_description, type_text, press_key, go_back, wait, read_page

EMAIL (3):
email_list, email_read, email_send (via IMAP/SMTP)

UTILITARIAS (5):
get_current_time, save_note, read_notes, get_weather, run_python

ARQUIVOS (3):
list_dir, read_file, write_file (workspace: C:\computer-agent\workspace)

SEGURANCA (1):
request_confirmation

## Testes que funcionaram

- "Que horas sao?" -> get_current_time()
- "Liste meus emails" -> email_list()
- "Crie um arquivo ola.txt" -> write_file()
- "Liste os arquivos do workspace" -> list_dir()

## Proximos passos

- agent-search (busca real na web sem API)
- Mais ferramentas de arquivo (delete_file, create_dir, move_file)
- Automacao do PC (run_command com confirmacao)

## WEB SEARCH - funcionando (24/09/2026)

O agente tem web_search(query) que:
- Pesquisa via DuckDuckGo HTML (scraping)
- Retorna titulo, URL e snippet de ate 5 resultados
- NAO abre navegador, NAO tem CAPTCHA, NAO precisa de API key

O System Prompt PRECISA instruir:
1. Chame a ferramenta
2. Veja o resultado
3. USE o resultado para responder com um RESUMO
4. NAO pare depois de chamar - SEMPRE responda com o resultado

Teste que funcionou:
Usuario: "Pesquise na web por melhores praticas Python e me de um resumo"
Agente: web_search() + resumo em 4 bullets

## FERRAMENTAS FINAIS (23)

NAVEGADOR (10): open_url, search_google, search_in_page, click_by_description,
                type_text, press_key, go_back, wait, read_page, click_element
EMAIL (3): email_list, email_read, email_send
UTILITARIAS (5): get_current_time, save_note, read_notes, get_weather, run_python
ARQUIVOS (3): list_dir, read_file, write_file
WEB SEARCH (1): web_search
SEGURANCA (1): request_confirmation

## Modelo recomendado: qwen2.5:7b

O llama3.1:8b entra em "modo narrador" com muitas ferramentas.
O qwen2.5:7b funciona PERFEITAMENTE para tool calling.
Use SEMPRE qwen2.5:7b como Base Model.

## Licoes aprendidas (24/09/2026)

1. MODELO: use qwen2.5:7b (nao llama3.1:8b)
   - llama3.1:8b entra em "modo narrador" com 23 ferramentas
   - qwen2.5:7b chama as ferramentas corretamente

2. CHAT NOVO: sempre use chat novo para tarefas criticas
   - Historico longo faz o LLM narrar em vez de chamar
   - Chat novo = contexto limpo

3. SYSTEM PROMPT: liste cada ferramenta com seus PARAMETROS EXATOS
   - open_url(url="...") - parametro: url (NAO query)
   - search_google(query="...") - parametro: query
   - Isso evita que o LLM invente parametros

4. PREFIRA search_google em vez de open_url com URL do Google
   - search_google JA tem fallback automatico para DuckDuckGo
   - open_url com URL do Google sofre CAPTCHA

5. FALLBACK: o open_url detecta CAPTCHA do Google e cai no DuckDuckGo
   - Mas search_google faz isso direto, mais simples

6. CHROME AUTO-RECUPERACAO: o start_browser() detecta contexto morto e recria
   - Voce nao precisa reiniciar o Uvicorn quando fecha o Chrome

## Encoding UTF-8 (24/09/2026)

O write_file e read_file agora usam UTF-8 com BOM (encoding="utf-8-sig"):
- Arquivos com acentos (á, ç, ã, é) ficam legiveis no Notepad, VS Code, etc.
- Sem isso, o Windows interpretava como Latin-1 e mostrava "OlÃ¡" em vez de "Olá"

Teste que funcionou:
- "Crie um arquivo encoding_test.txt com Olá, coração, ação"
- Get-Content mostra: Olá, coração, ação

## Licao sobre parametros do LLM

O LLM as vezes inventa os nomes dos parametros (ex: "filename" em vez de "caminho").
O Open WebUI traduz automaticamente, entao funciona mesmo assim.
Mas o ideal e sempre especificar os nomes EXATOS no System Prompt.

## VISAO (FASE 5) - 24/09/2026

O agente tem DUAS ferramentas de visao:

1. take_screenshot() - tira print e salva em C:\computer-agent\screenshots\
   NAO analisa. Use quando o usuario pedir "tire um print".

2. see_image(pergunta) - tira print E ANALISA com IA de visao (llm-eyes)
   Retorna a DESCRICAO do que esta na tela.
   Use quando o usuario pedir "olhe a tela", "o que voce ve", "descreva a tela".

## Como funciona o llm-eyes

O llm-eyes e um servidor de visao local que roda em http://127.0.0.1:8081.
Ele usa o modelo Qwen3.5-0.8B (pequeno, ~1 GB) como "olhos".

O servidor e iniciado com:
llama-server -m "C:\Users\Administrator\.cache\huggingface\hub\models--unsloth--Qwen3.5-0.8B-GGUF\snapshots\6ab461498e2023f6e3c1baea90a8f0fe38ab64d0\Qwen3.5-0.8B-UD-Q4_K_XL.gguf" --mmproj "C:\computer-agent\llm-eyes\models\mmproj-F16.gguf" -ngl 99 --host 0.0.0.0 --port 8081

## Nota sobre encoding

O modelo Qwen3.5-0.8B gera a resposta com encoding duplamente codificado (UTF-8 -> Latin-1).
O agent.py corrige com substituicoes manuais de caracteres.
O print() do Python mostra os acentos corretos.
O PowerShell exibe errado (mas o Open WebUI mostra correto).
