\# 🎯 ROADMAP — MYRA (Agente de Computador Local)



Última atualização: 04/10/2026



Este arquivo lista TUDO que falta fazer no projeto. Marca `\[x]` conforme avança.

Revê a cada 2 semanas — o que era prioridade muda.



\---



\## ✅ CONCLUÍDAS



\### Base (FASE 0-10, 15, 16, 17, 18, 19)

\- \[x] Servidor FastAPI (`agent.py`) com \~90 rotas

\- \[x] Navegador (Playwright): `open\_url`, `search\_google`, `search\_in\_page`, `click\_element`, `click\_by\_description`, `type\_text`, `press\_key`, `go\_back`, `wait`, `read\_page`

\- \[x] Visão (`see\_image` via llama-server Qwen3.5-0.8B)

\- \[x] Email (IMAP/SMTP Gmail): 10 rotas

\- \[x] Utilitárias: `get\_current\_time`, `save\_note`, `read\_notes`, `get\_weather`, `run\_python`

\- \[x] Arquivos (workspace): 7 rotas

\- \[x] Web search (DuckDuckGo scraping)

\- \[x] Automação PC (FASE 16): 12 rotas (mouse, teclado, janelas)

\- \[x] Chats (FASE 10): `pc\_get\_chats`, `pc\_remove\_chat`, `pc\_remove\_chats\_by\_search`, `pc\_remove\_all\_chats`, `pc\_rename\_chat`

\- \[x] CodeAgent (FASE 17): 21 tools

\- \[x] Sistema de confirmação de ações destrutivas



\### YouTube (FASE 20)

\- \[x] `youtube\_transcript`, `youtube\_summarize`, `youtube\_ask`, `youtube\_save`, `youtube\_list`, `youtube\_read`

\- \[x] FASE 20.1 — Detecção automática de idioma (`\_yt\_probe\_langs`, `\_yt\_escolher\_idioma`)

\- \[x] Fix de encoding de VTT duplamente codificado



\### Agente (FASE 22-light)

\- \[x] `tasks/simple\_task.py` — planner + loop + retry

\- \[x] Rota `/task\_simple`

\- \[x] Ferramentas registradas com descrições

\- \[x] Integração com Open WebUI (`task\_run` na Tool BrowserAgent)

\- \[x] Contexto acumulado entre passos

\- \[x] Fix do bug multilíngue (força português)



\### Infraestrutura

\- \[x] Ollama com CUDA v12

\- \[x] Open WebUI 0.11.4 em Docker

\- \[x] nginx proxy com `sub\_filter` (troca "Open WebUI" por "MYRA")

\- \[x] Scripts `iniciar\_myra.ps1` e `iniciar\_visao.ps1`

\- \[x] Chrome com perfil dedicado

\- \[x] `OPENWEBUI\_API\_KEY` salva permanentemente



\---



\## 🚧 PRÓXIMAS (ordem sugerida)



\### FASE 24 — Loop de Autonomia Real (o coração da MYRA)

\- \[ ] \*\*24.1\*\* — Loop adaptativo (LLM decide 1 passo por vez, olhando histórico)

\- \[ ] \*\*24.2\*\* — Ferramentas estruturadas:

&#x20; - \[ ] `search\_google\_structured` — retorna lista de links

&#x20; - \[ ] `web\_search\_structured` — retorna lista de links parseados

&#x20; - \[ ] `youtube\_search` — busca vídeos no YouTube

&#x20; - \[ ] `youtube\_channel\_latest` — último vídeo de um canal

&#x20; - \[ ] `get\_current\_url` — URL atual do navegador

&#x20; - \[ ] `read\_page\_structured` — devolve links + botões + campos em JSON

\- \[ ] \*\*24.3\*\* — Recuperação de erros (link quebrado, layout diferente, timeout)

\- \[ ] \*\*24.4\*\* — Verificação visual (screenshot + Vision após ação crítica)

\- \[ ] \*\*24.5\*\* — Persistência SQLite (tasks sobrevivem a restart)



\### FASE 22.5+ — Polimento do agente

\- \[ ] \*\*22.5\*\* — Melhorar o `responder` (respostas diretas, menos "o objetivo parece ser")

\- \[ ] \*\*22.6\*\* — Mais ferramentas no `task\_run` (email, arquivos, PC)

\- \[ ] \*\*22.7\*\* — Logs estruturados das tasks

\- \[ ] \*\*22.8\*\* — Modo "vou perguntar antes de agir"



\### FASE 34 — Telegram (controle remoto)

\- \[ ] \*\*34.1\*\* — Bot básico (criar bot, `telegram\_bot.py`, whitelist)

\- \[ ] \*\*34.2\*\* — Comandos especiais (`/status`, `/screenshot`, `/task`, `/yt`, `/email`, `/stop`, `/panic`)

\- \[ ] \*\*34.3\*\* — Segurança (rate limit, confirmação dupla, log)

\- \[ ] \*\*34.4\*\* — Auto-start (script `iniciar\_tudo.ps1` ou serviço Windows)

\- \[ ] \*\*34.5\*\* — Wake-on-LAN + túnel (PC sleep, DDNS, Cloudflare Tunnel)

\- \[ ] \*\*34.6\*\* — Multi-canal (Discord, WhatsApp, SMS, web app)



\---



\## 📅 MÉDIO PRAZO



\### Voz e áudio

\- \[ ] \*\*FASE 14\*\* — TTS + Whisper (MYRA fala e ouve)

\- \[ ] \*\*14.1\*\* — Wake word ("MYRA, ...")

\- \[ ] \*\*14.2\*\* — Conversa por voz contínua

\- \[ ] \*\*14.3\*\* — Escolha de voz (masculina/feminina, sotaque)

\- \[ ] \*\*14.4\*\* — Ditado por voz em qualquer campo

\- \[ ] \*\*FASE 20.5\*\* — Whisper pra vídeos sem legenda

\- \[ ] \*\*20.6\*\* — Suporte a outros sites de vídeo (Vimeo, etc.)

\- \[ ] \*\*20.7\*\* — Extrair áudio/MP3 de vídeos

\- \[ ] \*\*20.8\*\* — Baixar vídeo completo

\- \[ ] \*\*20.9\*\* — Playlists (transcrever/resumir playlist inteira)

\- \[ ] \*\*20.10\*\* — Cache de transcrições

\- \[ ] \*\*20.11\*\* — Vision sobre frames do vídeo



\### Geração de mídia

\- \[ ] \*\*FASE 12\*\* — Geração de imagem (API externa grátis)

\- \[ ] \*\*12.1\*\* — Edição de imagem (crop, resize, filtro)

\- \[ ] \*\*12.2\*\* — Geração de vídeo

\- \[ ] \*\*12.3\*\* — Remoção de fundo

\- \[ ] \*\*12.4\*\* — Upscale de imagem

\- \[ ] \*\*12.5\*\* — OCR de imagens



\### Arquivos

\- \[ ] \*\*15.6\*\* — Ler PDFs

\- \[ ] \*\*15.7\*\* — Ler Excel/CSV

\- \[ ] \*\*15.8\*\* — Ler Word/DOCX

\- \[ ] \*\*15.9\*\* — Ler PowerPoint/PPTX

\- \[ ] \*\*15.10\*\* — Converter formatos

\- \[ ] \*\*15.11\*\* — Acesso a arquivos FORA do workspace

\- \[ ] \*\*15.12\*\* — Compactar/descompactar (zip, 7z, tar)

\- \[ ] \*\*15.13\*\* — Hash de arquivos

\- \[ ] \*\*15.14\*\* — Comparar arquivos (diff)

\- \[ ] \*\*15.15\*\* — Monitorar mudanças em pasta

\- \[ ] \*\*15.16\*\* — Organizar Downloads automaticamente

\- \[ ] \*\*15.17\*\* — Classificar documentos por tipo



\### Navegador / Web

\- \[ ] \*\*Web 1\*\* — Baixar arquivos via navegador

\- \[ ] \*\*Web 2\*\* — Preencher formulários multi-step

\- \[ ] \*\*Web 3\*\* — Login automático em sites

\- \[ ] \*\*Web 4\*\* — Abrir/fechar/mudar entre abas

\- \[ ] \*\*Web 5\*\* — Screenshot de elemento específico

\- \[ ] \*\*Web 6\*\* — Extrair tabela de página HTML

\- \[ ] \*\*Web 7\*\* — Detectar CAPTCHA e resolver visualmente

\- \[ ] \*\*Web 8\*\* — Aguardar elemento aparecer

\- \[ ] \*\*Web 9\*\* — iFrames e shadow DOM

\- \[ ] \*\*Web 10\*\* — Cookies e localStorage

\- \[ ] \*\*Web 11\*\* — Bloquear anúncios/trackers

\- \[ ] \*\*Web 12\*\* — Modo headless opcional

\- \[ ] \*\*Web 13\*\* — Proxy/rotação de IP

\- \[ ] \*\*Web 14\*\* — Scraping estruturado



\### Computer Use avançado

\- \[ ] \*\*CU 1\*\* — Arrastar (drag and drop)

\- \[ ] \*\*CU 2\*\* — Copiar/colar via clipboard

\- \[ ] \*\*CU 3\*\* — Maximizar/minimizar janelas

\- \[ ] \*\*CU 4\*\* — Abrir aplicativo pelo nome

\- \[ ] \*\*CU 5\*\* — Fechar aplicativo

\- \[ ] \*\*CU 6\*\* — Processos (listar, matar)

\- \[ ] \*\*CU 7\*\* — Detectar janela por título parcial

\- \[ ] \*\*CU 8\*\* — Lidar com popups inesperados

\- \[ ] \*\*CU 9\*\* — Resolução adaptativa

\- \[ ] \*\*CU 10\*\* — Múltiplos monitores

\- \[ ] \*\*CU 11\*\* — Overlay em tempo real

\- \[ ] \*\*CU 12\*\* — Estados visuais (👁 OBSERVING, 🧠 THINKING, etc.)

\- \[ ] \*\*CU 13\*\* — Trajetória do mouse visível

\- \[ ] \*\*CU 14\*\* — Alvo destacado antes de clicar

\- \[ ] \*\*CU 15\*\* — Cancelamento visual



\### Vision avançado

\- \[ ] \*\*Vision 1\*\* — Trocar Qwen3.5-0.8B por modelo maior

\- \[ ] \*\*Vision 2\*\* — Identificar botões e elementos

\- \[ ] \*\*Vision 3\*\* — Retornar coordenadas de elemento

\- \[ ] \*\*Vision 4\*\* — Comparar tela antes/depois

\- \[ ] \*\*Vision 5\*\* — Detectar mudança de página

\- \[ ] \*\*Vision 6\*\* — Confirmar visualmente que ação funcionou

\- \[ ] \*\*Vision 7\*\* — Detectar erro visual

\- \[ ] \*\*Vision 8\*\* — Ler tabelas de imagens

\- \[ ] \*\*Vision 9\*\* — Ler menus e dropdowns

\- \[ ] \*\*Vision 10\*\* — OCR embutido

\- \[ ] \*\*Vision 11\*\* — Detecção de CAPTCHA visual

\- \[ ] \*\*Vision 12\*\* — Achar ícones por descrição textual



\### Coding Agent

\- \[ ] \*\*Code 1\*\* — Corrigir bugs automaticamente

\- \[ ] \*\*Code 2\*\* — Rodar projeto inteiro

\- \[ ] \*\*Code 3\*\* — Git (commit, branch, push via tool)

\- \[ ] \*\*Code 4\*\* — Criar projeto completo do zero

\- \[ ] \*\*Code 5\*\* — Analisar projeto inteiro

\- \[ ] \*\*Code 6\*\* — Instalar dependências automaticamente

\- \[ ] \*\*Code 7\*\* — Rodar testes e interpretar resultado

\- \[ ] \*\*Code 8\*\* — Loop: rodar → ver erro → corrigir → rodar

\- \[ ] \*\*Code 9\*\* — LSP integration

\- \[ ] \*\*Code 10\*\* — Refatorar múltiplos arquivos



\### Email / Comunicação

\- \[ ] \*\*Email 1\*\* — Baixar anexos

\- \[ ] \*\*Email 2\*\* — Salvar anexos no workspace

\- \[ ] \*\*Email 3\*\* — Analisar anexos

\- \[ ] \*\*Email 4\*\* — Encaminhar email

\- \[ ] \*\*Email 5\*\* — Criar rascunho

\- \[ ] \*\*Email 6\*\* — Arquivar email

\- \[ ] \*\*Email 7\*\* — Identificar emails que exigem resposta

\- \[ ] \*\*Email 8\*\* — Detectar prazos e compromissos

\- \[ ] \*\*Email 9\*\* — Resumir thread inteira

\- \[ ] \*\*Email 10\*\* — Aplicar labels/tags

\- \[ ] \*\*Email 11\*\* — Busca avançada

\- \[ ] \*\*Email 12\*\* — Suporte a múltiplas contas



\### Info do mundo

\- \[ ] \*\*Info 1\*\* — Notícias (RSS ou API)

\- \[ ] \*\*Info 2\*\* — Preços (ações, cripto, produtos)

\- \[ ] \*\*Info 3\*\* — Mapas / rotas / localização

\- \[ ] \*\*Info 4\*\* — Tradução automática

\- \[ ] \*\*Info 5\*\* — Cotação de moedas

\- \[ ] \*\*Info 6\*\* — Calendário (Google Calendar)

\- \[ ] \*\*Info 7\*\* — Contatos (Google Contacts)

\- \[ ] \*\*Info 8\*\* — Busca em PDFs/documentos locais (RAG)



\### Análise de dados

\- \[ ] \*\*Data 1\*\* — Abrir CSV direto

\- \[ ] \*\*Data 2\*\* — Abrir Excel direto

\- \[ ] \*\*Data 3\*\* — Análise automática de gastos

\- \[ ] \*\*Data 4\*\* — Dashboard interativo

\- \[ ] \*\*Data 5\*\* — Alertas baseados em dados

\- \[ ] \*\*Data 6\*\* — Exportar gráficos



\### Windows / Sistema

\- \[ ] \*\*Win 1\*\* — Instalar software (winget/choco)

\- \[ ] \*\*Win 2\*\* — Atualizar software

\- \[ ] \*\*Win 3\*\* — Configurar aplicações

\- \[ ] \*\*Win 4\*\* — Diagnóstico de problemas

\- \[ ] \*\*Win 5\*\* — Monitorar recursos (CPU, RAM, disco, GPU)

\- \[ ] \*\*Win 6\*\* — Alertas de sistema

\- \[ ] \*\*Win 7\*\* — Backup automático

\- \[ ] \*\*Win 8\*\* — Restaurar backup



\### Terminal / Execução

\- \[ ] \*\*Term 1\*\* — Interpretar output e decidir próximo comando

\- \[ ] \*\*Term 2\*\* — Comandos PowerShell estruturados

\- \[ ] \*\*Term 3\*\* — Comandos CMD estruturados

\- \[ ] \*\*Term 4\*\* — npm/yarn/pnpm

\- \[ ] \*\*Term 5\*\* — pip/poetry/uv

\- \[ ] \*\*Term 6\*\* — Docker (list, run, stop, logs)

\- \[ ] \*\*Term 7\*\* — Ollama (list, pull, run)

\- \[ ] \*\*Term 8\*\* — Git (status, diff, commit, push, pull, branch)

\- \[ ] \*\*Term 9\*\* — Timeout adaptativo

\- \[ ] \*\*Term 10\*\* — Comando em background + polling



\### Agendamento / Notificações

\- \[ ] \*\*FASE 31\*\* — Scheduler (tarefas em horários)

\- \[ ] \*\*31.1\*\* — Tarefas recorrentes

\- \[ ] \*\*31.2\*\* — Tarefas com delay

\- \[ ] \*\*FASE 32\*\* — Notificações Windows (toast)

\- \[ ] \*\*32.1\*\* — Notificações por voz

\- \[ ] \*\*32.2\*\* — Notificações por email

\- \[ ] \*\*32.3\*\* — Notificações Telegram/Discord



\### Memória

\- \[ ] \*\*FASE 33\*\* — Memória de preferências

\- \[ ] \*\*33.1\*\* — Memória de contexto de projetos

\- \[ ] \*\*33.2\*\* — Memória de tarefas (histórico)

\- \[ ] \*\*33.3\*\* — Memória episódica

\- \[ ] \*\*33.4\*\* — Schema de memória

\- \[ ] \*\*33.5\*\* — Busca semântica na memória

\- \[ ] \*\*33.6\*\* — Esquecer/apagar memória específica



\### Memória de ferramentas

\- \[ ] \*\*Mem 1\*\* — Router inteligente (saber qual ferramenta usar)

\- \[ ] \*\*Mem 2\*\* — Não repetir erro conhecido

\- \[ ] \*\*Mem 3\*\* — Preferir solução que funcionou antes

\- \[ ] \*\*Mem 4\*\* — Histórico de sessões

\- \[ ] \*\*Mem 5\*\* — Sumarização periódica



\### Segurança

\- \[ ] \*\*Sec 1\*\* — Cofre de senhas (criptografado)

\- \[ ] \*\*Sec 2\*\* — 2FA para ações críticas

\- \[ ] \*\*Sec 3\*\* — Log de tudo que a MYRA faz

\- \[ ] \*\*Sec 4\*\* — Reverter ação destrutiva (undo)

\- \[ ] \*\*Sec 5\*\* — Sandbox para execução de código

\- \[ ] \*\*Sec 6\*\* — Limites de gasto (se usar API paga)



\### Dispositivos

\- \[ ] \*\*Dev 1\*\* — Acesso pelo celular (web app)

\- \[ ] \*\*Dev 2\*\* — App desktop nativo (Electron/Tauri)

\- \[ ] \*\*Dev 3\*\* — Sincronização entre máquinas

\- \[ ] \*\*Dev 4\*\* — Acesso remoto (fora de casa)



\### Testes / Qualidade

\- \[ ] \*\*Test 1\*\* — Testes automatizados do `agent.py`

\- \[ ] \*\*Test 2\*\* — Testes das Tools

\- \[ ] \*\*Test 3\*\* — CI/CD no GitHub

\- \[ ] \*\*Test 4\*\* — Health check endpoint

\- \[ ] \*\*Test 5\*\* — Métricas de uso (latência, erros)

\- \[ ] \*\*Test 6\*\* — Teste de carga



\### Documentação

\- \[ ] \*\*Doc 1\*\* — Atualizar README.md

\- \[ ] \*\*Doc 2\*\* — Documentar cada tool

\- \[ ] \*\*Doc 3\*\* — Documentar arquitetura

\- \[ ] \*\*Doc 4\*\* — Guia de troubleshooting

\- \[ ] \*\*Doc 5\*\* — Vídeo demo

\- \[ ] \*\*Doc 6\*\* — Diagrama de fluxo



\---



\## 🔮 LONGO PRAZO



\### Meta / Estratégico

\- \[ ] \*\*Meta 1\*\* — MYRA rodando 24/7 em background

\- \[ ] \*\*Meta 2\*\* — MYRA acorda sozinha e faz tarefas agendadas

\- \[ ] \*\*Meta 3\*\* — MYRA aprende preferências do usuário

\- \[ ] \*\*Meta 4\*\* — MYRA proativa

\- \[ ] \*\*Meta 5\*\* — MYRA multi-usuário (perfis)

\- \[ ] \*\*Meta 6\*\* — Auto-diagnóstico

\- \[ ] \*\*Meta 7\*\* — Auto-recovery

\- \[ ] \*\*Meta 8\*\* — Multi-agent (Researcher, Coder, etc.)



\### FASE 40 — UI própria da MYRA

Só quando o Open WebUI virar gargalo real.



\- \[ ] \*\*40.1\*\* — Design da UI (Figma ou similar)

\- \[ ] \*\*40.2\*\* — Frontend React/Svelte do zero

\- \[ ] \*\*40.3\*\* — WebSocket entre frontend e `agent.py`

\- \[ ] \*\*40.4\*\* — Chat com markdown rendering

\- \[ ] \*\*40.5\*\* — Sidebar de conversas

\- \[ ] \*\*40.6\*\* — Painel de tasks em execução

\- \[ ] \*\*40.7\*\* — Overlay visual de computer use

\- \[ ] \*\*40.8\*\* — Botões de ação rápida

\- \[ ] \*\*40.9\*\* — Migração do Open WebUI

\- \[ ] \*\*40.10\*\* — Deploy e testes



\*\*Gatilhos pra começar a FASE 40:\*\*

\- FASE 24+ completa (agent maduro)

\- Open WebUI limita features que a MYRA precisa (overlay, task manager visual)

\- Tempo dedicado (2-4 semanas)



\---



\## ❌ REMOVIDAS / CANCELADAS



\### FASE 9 — Customização profunda do Open WebUI

\*\*Decisão (04/10/2026):\*\* manter Open WebUI oficial + customizações mínimas. Já temos o suficiente (nginx proxy, Tools, modo Local Agent).

\- \~\~9.5 — Remover "(Open WebUI)" do título\~\~

\- \~\~9.6 — Trocar textos internos\~\~

\- \~\~9.7 — Logo e favicon custom\~\~

\- \~\~9.8 — CSS custom\~\~

\- \~\~9.9 — JS custom\~\~

\- \~\~9.10 — System prompt global\~\~

\- \~\~9.11 — Splash screen custom\~\~

\- \~\~9.12 — Modelo "MYRA" como padrão\~\~

\- \~\~9.13 — Fork do Open WebUI\~\~ (cancelado)

\- \~\~9.14 — UI própria do zero\~\~ (movida pra FASE 40, futuro distante)



\---



\## 📊 RESUMO POR ÁREA



| Área | Itens |

|---|---|

| FASE 22-light (pendente commit) | 3 |

| Autonomia (FASE 24 + 22.x) | 18 |

| Interface / Canais (FASE 34) | 17 |

| Voz / Áudio | 5 |

| YouTube / Mídia | 12 |

| Geração de mídia | 6 |

| Arquivos | 12 |

| Navegador / Web | 14 |

| Computer Use | 15 |

| Vision | 12 |

| Coding Agent | 10 |

| Email / Comunicação | 12 |

| Info do mundo | 8 |

| Análise de dados | 6 |

| Windows / Sistema | 8 |

| Terminal | 10 |

| Agendamento / Notificações | 7 |

| Memória | 7 |

| Memória de ferramentas | 5 |

| Segurança | 6 |

| Dispositivos | 4 |

| Testes | 6 |

| Documentação | 6 |

| Meta / Estratégico | 8 |

| FASE 40 (UI própria) | 10 |



\*\*Total: \~230 itens.\*\*



\---



\## 🎯 PRÓXIMA AÇÃO



\*\*Antes de começar qualquer fase nova:\*\*



1\. Commit da FASE 22-light:

&#x20;  ```powershell

&#x20;  cd C:\\computer-agent

&#x20;  git add agent.py tasks/ tools/browseragent.py

&#x20;  git commit -m "feat: FASE 22-light - task simples com planner + retry + integracao chat"

&#x20;  git push

