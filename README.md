# Computer Agent + MYRA

Agente de navegador local controlado por linguagem natural, integrado ao MYRA (Open WebUI customizado).

## Arquitetura

Usuario -> MYRA (Docker, 8082) -> LLM local (Ollama, qwen2.5:7b)
                |
                v
         Tool BrowserAgent -> agent.py (FastAPI, 8000) -> Playwright -> Chromium -> Internet

## Componentes

| Componente | Porta | Funcao |
|---|---|---|
| MYRA (Open WebUI customizado) | 8082 (externa) | Interface do chat |
| open-webui-custom | 8080 (interna) | Container Open WebUI com WEBUI_NAME=MYRA |
| myra-proxy | 8082 | Nginx proxy que remove "(Open WebUI)" do titulo |
| agent.py (Uvicorn) | 8000 | Servidor FastAPI + Playwright |
| Ollama | 11434 | LLM local (qwen2.5:7b) |
| llm-eyes | 8081 | Servidor de visao (Qwen3.5-0.8B) |

## MYRA - Open WebUI customizado

O MYRA e o Open WebUI renomeado. Para isso, usamos:

1. Variavel de ambiente WEBUI_NAME=MYRA no container do Open WebUI.
2. Proxy reverso Nginx na porta 8082 que remove o sufixo "(Open WebUI)" do titulo e da sidebar.

### Como acessar

    http://localhost:8082

ATENCAO: sempre use a porta 8082 para ver o MYRA sem o sufixo. A porta 8080 mostra o titulo original.

### Arquitetura do MYRA

    Navegador -> localhost:8082 (Nginx) -> open-webui-custom:8080 (Open WebUI)

### Configuracao do Nginx

O arquivo fica em C:\computer-agent\webui-custom\nginx.conf:

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://open-webui-custom:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Accept-Encoding "";

            proxy_buffering off;
            proxy_cache off;

            sub_filter_once off;
            sub_filter '<title>Open WebUI</title>' '<title>MYRA</title>';
            sub_filter '</head>' '<script>...</script></head>';
        }
    }

O JavaScript injetado corrige o titulo e a sidebar em tempo real, mesmo depois que o Svelte tenta reescreve-los.

### Como recriar o proxy (se o nginx.conf mudar)

    docker rm -f myra-proxy
    docker run -d --name myra-proxy -p 8082:80 -v C:\computer-agent\webui-custom\nginx.conf:/etc/nginx/conf.d/default.conf --link open-webui-custom:open-webui-custom nginx:alpine

### Como recriar o Open WebUI (se precisar)

    docker rm -f open-webui-custom
    docker run -d --name open-webui-custom -p 8080:8080 -e WEBUI_NAME=MYRA -v open-webui:/app/backend/data --restart always ghcr.io/open-webui/open-webui:main

ATENCAO: o volume "open-webui" guarda todos os dados (conversas, usuarios, configuracoes). Nunca remova esse volume.

### Favicons e logo customizados

O MYRA usa favicons e logo proprios (o olho roxo/azul). Para isso, usamos:

1. Uma pasta no host com as imagens: C:\computer-agent\webui-custom\Favicons\
2. O Nginx serve esses arquivos no lugar dos originais do Open WebUI.

#### Arquivos necessarios

| Arquivo | Tamanho | Funcao |
|---|---|---|
| favicon.png | 512x512 | Favicon principal |
| favicon.ico | multi | Navegadores antigos |
| favicon.svg | 512x512 | Navegadores modernos |
| favicon-96x96.png | 96x96 | Android/Chrome |
| favicon-32x32.png | 32x32 | Navegadores antigos |
| favicon-16x16.png | 16x16 | Aba do navegador |
| apple-touch-icon.png | 180x180 | iOS/Safari |
| logo.png | 512x512 | Logo da sidebar |
| MYRALOGO.jpeg | original | Imagem original |

#### Como gerar os favicons

Se voce trocar a imagem original (MYRALOGO.jpeg), rode:

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    python C:\computer-agent\webui-custom\Favicons\gerar_favicons_transparente.py
    docker restart myra-proxy

O script:
1. Abre o MYRALOGO.jpeg
2. Remove o fundo preto (torna transparente)
3. Gera os 8 arquivos de favicon
4. Salva tudo em Favicons\

#### Como recriar o myra-proxy com os favicons

    docker rm -f myra-proxy
    docker run -d --name myra-proxy -p 8082:80 -v C:\computer-agent\webui-custom\nginx.conf:/etc/nginx/conf.d/default.conf -v C:\computer-agent\webui-custom\Favicons:/usr/share/nginx/html --link open-webui-custom:open-webui-custom nginx:alpine

ATENCAO: a flag -v extra monta a pasta Favicons em /usr/share/nginx/html dentro do container. Sem ela, o Nginx nao encontra os favicons customizados.

#### Ajuste do limite de transparencia

O script usa limite = 30 para remover o preto. Se sobrarem bordas escuras, aumente para 40 ou 50. Se apagar partes do logo, diminua para 20.

Edite a linha no gerar_favicons_transparente.py:

    limite = 30   # ajuste aqui

E rode de novo.



## FASE 19 - Guia de reinstalacao

O projeto tem um guia completo de reinstalacao em `C:\computer-agent\GUIA.md`.

O guia cobre:
- Pre-requisitos (Python, Node, Git, Docker, Ollama)
- Estrutura de pastas
- Passo a passo de cada configuracao (Python, Ollama, Docker, MYRA, llm-eyes, agent.py)
- Solucao de problemas
- Checklist final

Tambem foi criado o `requirements.txt` com as dependencias Python:

    fastapi==0.141.1
    uvicorn==0.53.0
    pydantic==2.13.5
    playwright==1.63.0
    requests==2.34.2
    pillow==12.3.0

## Acoes disponiveis no agent.py

### Navegador (10)

| Rota | Acao |
|---|---|
| POST /open_url | Abre uma URL |
| POST /search_google | Pesquisa no Google |
| POST /search_in_page | Pesquisa na pagina atual |
| POST /click_element | Clica por texto ou seletor CSS |
| POST /click_by_description | Clica por descricao (fallback) |
| POST /type_text | Digita em um campo |
| POST /press_key | Pressiona uma tecla |
| POST /go_back | Volta uma pagina |
| POST /wait | Espera N segundos |
| POST /read_page | Le texto + lista de elementos clicaveis |

### Email (3) - via IMAP/SMTP

| Rota | Acao |
|---|---|
| POST /email_list | Lista os ultimos emails |
| POST /email_read | Le um email pelo indice |
| POST /email_send | Envia email (SMTP) |

### Utilitarias (5)

| Rota | Acao |
|---|---|
| POST /get_current_time | Retorna a hora atual |
| POST /save_note | Salva uma nota |
| POST /read_notes | Le as notas |
| POST /get_weather | Retorna o clima |
| POST /run_python | Executa codigo Python |

### Arquivos (3) - restrito ao workspace

| Rota | Acao |
|---|---|
| POST /list_dir | Lista arquivos/pastas |
| POST /read_file | Le um arquivo |
| POST /write_file | Cria/sobrescreve arquivo |

### Web Search (1)

| Rota | Acao |
|---|---|
| POST /web_search | Pesquisa via DuckDuckGo HTML (sem API key) |

### Visao (2)

| Rota | Acao |
|---|---|
| POST /take_screenshot | Tira print e salva em screenshots\ |
| POST /see_image | Tira print E analisa com IA de visao |

### Seguranca (1)

| Rota | Acao |
|---|---|
| POST /request_confirmation | Pede confirmacao antes de acao critica |

## FASE 15 - Ferramentas de arquivo avancadas

O agente tem 7 ferramentas de arquivo (3 originais + 4 novas):

| Ferramenta | O que faz | Precisa confirmacao? |
|---|---|---|
| list_dir(caminho) | Lista arquivos/pastas | Nao |
| read_file(caminho) | Le um arquivo | Nao |
| write_file(caminho, conteudo) | Cria/sobrescreve | Nao |
| create_dir(caminho) | Cria pasta | Nao |
| search_in_files(termo, extensao) | Busca texto nos arquivos | Nao |
| delete_file(caminho) | Apaga arquivo | SIM |
| move_file(origem, destino) | Move/renomeia | SIM |

### Exemplos

- "Crie uma pasta chamada teste" -> create_dir(caminho="teste")
- "Crie um arquivo ola.txt com 'Ola'" -> write_file(caminho="ola.txt", conteudo="Ola")
- "Procure a palavra MYRA nos arquivos" -> search_in_files(termo="MYRA", extensao=".txt")
- "Mova o arquivo a.txt para b.txt" -> request_confirmation + move_file
- "Apague o arquivo a.txt" -> request_confirmation + delete_file

## FASE 8 - Confirmacao robusta

O agente bloqueia acoes destrutivas ate o usuario confirmar.

### Fluxo simplificado (2 etapas)

1. LLM chama `request_confirmation(acao, detalhes)` -> cria pendencia
2. Usuario responde "sim"
3. LLM chama a ferramenta destrutiva DIRETO (delete_file, move_file, email_send)

### Exemplo

    Usuario: "Apague o arquivo teste.txt"
    Agente: request_confirmation(acao="apagar arquivo", detalhes="teste.txt")
    Agente: "Confirma que deseja apagar teste.txt? (sim/nao)"
    Usuario: "sim"
    Agente: delete_file(caminho="teste.txt")
    Agente: "Pronto! Apaguei o arquivo teste.txt."

### Bloqueio real

Se o LLM tentar chamar `delete_file` sem antes chamar `request_confirmation`, o `agent.py` retorna:

    {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}

### Rotas de confirmacao

| Rota | O que faz |
|---|---|
| POST /request_confirmation | Cria a pendencia (acao, detalhes) |
| POST /confirm_action | (opcional) Marca como confirmada |
| POST /cancel_confirmation | Cancela a pendencia |

### Timeout

A confirmacao expira em **5 minutos**. Depois disso, o `agent.py` limpa a pendencia e a acao precisa ser solicitada novamente.

## Estrutura de arquivos

    C:\computer-agent\
    - agent.py                  # Servidor FastAPI + Playwright
    - start.ps1                 # Script de inicializacao
    - status.ps1                # Script de verificacao
    - abrir_tudo.ps1            # Sobe tudo (Docker + Ollama + agent + llm-eyes)
    - README.md                 # Este arquivo
    - venv\                     # Ambiente virtual Python
    - workspace\                # Area restrita do agente (arquivos)
    - screenshots\              # Prints tirados pelo agente
    - chromium_profile\         # Perfil persistente do Chromium
    - llm-eyes\                 # Servidor de visao
    - webui-custom\
      - nginx.conf              # Configuracao do proxy reverso MYRA

## Como iniciar tudo

### Inicio rapido

Abra o PowerShell em C:\computer-agent e rode:

    .\abrir_tudo.ps1

Isso sobe:
- Docker Desktop (se nao estiver rodando)
- Ollama com CUDA v12
- Container open-webui-custom
- Container myra-proxy (Nginx)
- agent.py (Uvicorn)
- llm-eyes (visao)

### Inicio manual

Janela 1 - Uvicorn (agent.py):

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    uvicorn agent:app --host 127.0.0.1 --port 8000

Janela 2 - Ollama:

    $env:OLLAMA_LLM_LIBRARY="cuda_v12"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

Janela 3 - Docker (MYRA + Nginx):

    docker start open-webui-custom
    docker start myra-proxy

## Configuracao do Local Agent

- Base Model: qwen2.5:7b (NAO use llama3.1:8b - entra em "modo narrador")
- Function Calling: Native
- max_tokens: 2048
- num_ctx (Ollama): 8192 (obrigatorio - com 4096 as 23 ferramentas nao cabem)
- Tool: BrowserAgent marcada

### Por que qwen2.5:7b?

O llama3.1:8b "narra" as acoes em vez de chama-las quando ha muitas ferramentas. O qwen2.5:7b foi treinado para tool calling e funciona perfeitamente.

## Configuracao critica

### Ollama precisa de CUDA v12

A placa RTX A2000 do notebook tem problema com CUDA v13 (crash 0xc0000409). Sempre inicie o Ollama com:

    $env:OLLAMA_LLM_LIBRARY="cuda_v12"

Variavel permanente (recomendado):
1. Win + R -> sysdm.cpl -> Enter
2. Aba Avancado -> Variaveis de Ambiente
3. Variaveis do usuario -> Novo
4. Nome: OLLAMA_LLM_LIBRARY
5. Valor: cuda_v12

### Open WebUI (Docker)

- URL do Ollama no MYRA: http://host.docker.internal:11434
- URL do agent.py na Tool: http://host.docker.internal:8000

### Email via IMAP/SMTP

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

## Como usar

1. Abra http://localhost:8082
2. New Chat
3. Selecione o modelo Local Agent
4. Digite comandos em portugues

### Exemplos

- Abra o Google
- Pesquise por Open WebUI
- Abra https://example.com
- Clique no link
- Leia a pagina
- Espere 3 segundos
- Pressione Enter
- Que horas sao?
- Liste meus emails
- Crie um arquivo ola.txt
- Pesquise na web por melhores praticas Python
- Olhe a tela e me diga o que esta vendo

## Solucao de problemas

### O titulo do MYRA volta a mostrar "(Open WebUI)"

Cache do navegador. Aperte Ctrl + Shift + R.

### Os modelos sumiram do MYRA

O Ollama foi reiniciado e o MYRA nao percebeu.
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

### O Nginx nao aplica o sub_filter

Verifique se o modulo sub_filter esta disponivel:

    docker exec myra-proxy nginx -V 2>&1 | Select-String "sub"

Deve aparecer --with-http_sub_module.

### Porta 8082 ja em uso

Outro container esta usando essa porta. Verifique:

    netstat -ano | findstr ":8082"

## Modelos instalados

- qwen2.5:7b (usado pelo Local Agent - recomendado)
- qwen2.5:3b (1.9 GB - fallback)
- llama3.1:8b (4.9 GB - NAO use com muitas ferramentas)
- R4C3R/qwen2.5-coder-3b-heretic (6.2 GB)
- refinedneuro/refinedtoolcallv5-3b (2.5 GB)
- goekdenizguelmez/JOSIE:4b-instruct-q4_k_m (2.5 GB)
- gemma2:2b (1.6 GB)

## Limitacoes

1. Modelos 3B tem dificuldade com multi-step.
2. A GPU RTX A2000 Laptop tem 4 GB dedicados. Modelos > 4 GB vao para CPU (lento).
3. Cada acao e uma mensagem separada (loop SEE->THINK->ACT ainda nao implementado).
4. Sem confirmacao antes de acoes irreversiveis (exceto via request_confirmation).

## Licoes aprendidas

1. MODELO: use qwen2.5:7b (nao llama3.1:8b).
2. CHAT NOVO: sempre use chat novo para tarefas criticas.
3. SYSTEM PROMPT: liste cada ferramenta com seus parametros exatos.
4. PREFIRA search_google em vez de open_url com URL do Google.
5. FALLBACK: o open_url detecta CAPTCHA do Google e cai no DuckDuckGo.
6. CHROME AUTO-RECUPERACAO: o start_browser() detecta contexto morto e recria.
7. ENCODING UTF-8: write_file e read_file usam encoding="utf-8-sig" (BOM) para acentos.

## Historico

- 23/09/2026 - Construcao inicial. Virada: click_by_description com fallback.
- 24/09/2026 - Email (IMAP/SMTP), arquivos, web search, visao (llm-eyes + Qwen3.5-0.8B).
- 25/09/2026 - Visao funcionando. MYRA (Open WebUI customizado) na porta 8082 com proxy Nginx.
- 25/09/2026 - MYRA: favicon e logo customizados (olho roxo/azul, fundo transparente).
- 25/09/2026 - WebSocket funcionando (sem "Conexao perdida").
- 25/09/2026 - FASE 15: create_dir, delete_file, move_file, search_in_files.
- 25/09/2026 - FASE 8: confirmacao robusta (fluxo simplificado de 2 etapas).
- 25/09/2026 - FASE 19: GUIA.md + requirements.txt.

## Proximas fases

Concluidas:
- FASE 0: Base
- FASE 1: OPEN/SEARCH
- FASE 2: CLICK/TYPE/PRESS/WAIT/BACK
- FASE 3: READ/DOM
- FASE 4: Loop SEE -> THINK -> ACT
- FASE 5: Screenshots + visao
- FASE 6: Integracao Open WebUI
- FASE 8: Confirmacao robusta (2 etapas)
- FASE 9: Customizacao da interface (MYRA, favicon, logo)
- FASE 15: Ferramentas de arquivo avancadas
- FASE 19: Guia de reinstalacao

Pendentes:
- FASE 7: Agente autonomo
- FASE 10: Apagar chats em lote (1-2h)
- FASE 11: Responder com botoes (2-4h)
- FASE 12: Geracao de imagem (via API externa, 1h)
- FASE 13: Geracao de video (INVIAVEL - hardware)
- FASE 14: TTS + Whisper (1-2h)
- FASE 16: Automacao do PC (run_command, 1-2h)
- FASE 17: Agente de codigo (pip, git, scripts, 1-2h)
- FASE 18: Criar/Marcar/mover/apagar emails (1h)

## Licenca e branding

O Open WebUI (base do MYRA) tem uma licenca BSD-3 com restricoes de branding. O WEBUI_NAME=MYRA e suportado oficialmente. A remocao do sufixo "(Open WebUI)" via proxy reverso e uma customizacao tecnica - para uso pessoal/local, nao ha problema. Para redistribuicao, verifique os termos da licenca: https://docs.openwebui.com/license
