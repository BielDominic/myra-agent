import re

caminho = r"C:\computer-agent\README.md"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Adicionar secao FASE 15 (depois de "Acoes disponiveis no agent.py")
# ============================================================

marcador_fase15 = "## Estrutura de arquivos"

secao_fase15 = """## FASE 15 - Ferramentas de arquivo avancadas

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

"""

if marcador_fase15 in conteudo:
    conteudo = conteudo.replace(marcador_fase15, secao_fase15 + marcador_fase15, 1)
    print("[OK] FASE 15 + FASE 8 inseridas")
else:
    print("[ERRO] Marcador '## Estrutura de arquivos' nao encontrado")

# ============================================================
# 2. Adicionar secao FASE 19 (depois de "MYRA - Open WebUI customizado")
# ============================================================

marcador_fase19 = "## Acoes disponiveis no agent.py"

secao_fase19 = """## FASE 19 - Guia de reinstalacao

O projeto tem um guia completo de reinstalacao em `C:\\computer-agent\\GUIA.md`.

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

"""

if marcador_fase19 in conteudo:
    conteudo = conteudo.replace(marcador_fase19, secao_fase19 + marcador_fase19, 1)
    print("[OK] FASE 19 inserida")
else:
    print("[ERRO] Marcador '## Acoes disponiveis no agent.py' nao encontrado")

# ============================================================
# 3. Atualizar Historico
# ============================================================

historico_antigo = """## Historico

- 23/09/2026 - Construcao inicial. Virada: click_by_description com fallback.
- 24/09/2026 - Email (IMAP/SMTP), arquivos, web search, visao (llm-eyes + Qwen3.5-0.8B).
- 25/09/2026 - Visao funcionando. MYRA (Open WebUI customizado) na porta 8082 com proxy Nginx."""

historico_novo = """## Historico

- 23/09/2026 - Construcao inicial. Virada: click_by_description com fallback.
- 24/09/2026 - Email (IMAP/SMTP), arquivos, web search, visao (llm-eyes + Qwen3.5-0.8B).
- 25/09/2026 - Visao funcionando. MYRA (Open WebUI customizado) na porta 8082 com proxy Nginx.
- 25/09/2026 - MYRA: favicon e logo customizados (olho roxo/azul, fundo transparente).
- 25/09/2026 - WebSocket funcionando (sem "Conexao perdida").
- 25/09/2026 - FASE 15: create_dir, delete_file, move_file, search_in_files.
- 25/09/2026 - FASE 8: confirmacao robusta (fluxo simplificado de 2 etapas).
- 25/09/2026 - FASE 19: GUIA.md + requirements.txt."""

if historico_antigo in conteudo:
    conteudo = conteudo.replace(historico_antigo, historico_novo, 1)
    print("[OK] Historico atualizado")
else:
    print("[AVISO] Marcador de Historico nao encontrado")

# ============================================================
# 4. Atualizar Proximas fases
# ============================================================

proximas_antigo = """## Proximas fases

- FASE 4: Loop SEE -> THINK -> ACT
- FASE 5: Screenshots + visao (concluido)
- FASE 7: Agente autonomo
- FASE 8: Confirmacao antes de acoes criticas
- FASE B2: agent-search (busca real na web sem API)
- FASE C: mais ferramentas de arquivo (delete_file, create_dir, move_file)
- FASE D: automacao do PC (run_command com confirmacao)"""

proximas_novo = """## Proximas fases

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
- FASE 18: Criar/Marcar/mover/apagar emails (1h)"""

if proximas_antigo in conteudo:
    conteudo = conteudo.replace(proximas_antigo, proximas_novo, 1)
    print("[OK] Proximas fases atualizado")
else:
    print("[AVISO] Marcador de Proximas fases nao encontrado")

# ============================================================
# 5. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] README.md atualizado com FASE 8, 15 e 19")
