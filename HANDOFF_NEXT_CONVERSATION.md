# MYRA — Handoff para próxima conversa
Atualizado: 2026-10-25
Repo local: `C:\computer-agent`
Branch: `feature/fase26-vision-fixes`
Remote: `origin/feature/fase26-vision-fixes`
Identidade de commit obrigatória: `BielDominic <gabrielenrique817@gmail.com>`

## Instrução principal do usuário
O usuário autorizou autonomia para continuar implementando e testando sem pedir autorização a cada etapa; só declarar o projeto concluído quando estiver 100% completo. Commits e pushes devem usar a identidade do usuário, nunca Codex. Não incluir backups, logs, segredos nem arquivos locais de memória no Git.

## Decisão de escopo
Em 2026-10-25 o usuário decidiu **pular/deferir por enquanto a parte de iOS nativo** e começar as próximas fases. Não remover o código iOS existente. Deixar para fase final: instalar/assinar o app no iPhone, Apple Developer/App Group, TestFlight, validação Siri/WidgetKit no dispositivo, APNs, CarPlay e polimento visual/interface. A Fase 28 não está 100% concluída: a infraestrutura remota do PC foi validada, mas ainda faltam comandos reais do Telegram e validação no iPhone.

## Estado da Fase 28 — Controle Mobile
Documento detalhado: `PHASE28_MOBILE.md`. Roadmap: `ROADMAP.md`.
- Fase 28 registrada em 84%; não inflar esse percentual.
- PC Windows H9746J3; Remote Desktop Commander device ID `77945ae2-1719-4305-97ce-cb1028fb31e9`.
- Repo em `C:\computer-agent`, branch `feature/fase26-vision-fixes`.
- Tailscale ativo no Windows; iPhone peer `iphone181` online no tailnet, IPv4 `100.112.204.30`; ping via DERP validado.
- URL Tailscale HTTPS: `https://h9746j3.tail648f78.ts.net/remote/v1`.
- Tailscale Serve encaminha exclusivamente `/remote/v1` para `http://127.0.0.1:8000/remote/v1`; sem Funnel e sem portas públicas. Backend escuta somente em loopback.
- Token remoto de 256 bits está na variável de ambiente do usuário Windows `MYRA_REMOTE_API_TOKEN`; não revelar, não imprimir, não commitar. Para colocar o token na área de transferência localmente sem exibi-lo: `Set-Clipboard ([Environment]::GetEnvironmentVariable('MYRA_REMOTE_API_TOKEN', 'User'))`.
- API Bearer: `GET /remote/v1/status`, `POST /remote/v1/task`, `POST /remote/v1/cancel`. Bearer válido HTTP 200; ausente/inválido HTTP 401; rotas externas ao prefixo HTTPS retornam 404; objetivo vazio e max_passos=51 retornam 422; tarefa simultânea retorna 409; cancelamento retorna estado idle.
- Testes reais via HTTPS/Tailscale: tarefas abriram Calculadora e Notepad e chegaram a `done`, com janela visível confirmada por UI Automation e síntese LLM normal. Ollama recuperado, 15 modelos disponíveis.
- Inicialização endurecida: `scripts/stop_myra_backend.ps1` encerra somente processos identificados como backend MYRA e aborta se a porta 8000 pertencer a outro processo; `scripts/import_user_environment.ps1` recarrega env User sem imprimir segredos; `scripts/ensure_ollama.ps1` integrado em `abrir_tudo.ps1` e `iniciar_myra.ps1`.
- Telegram long polling/allowlist e comandos estão implementados em `tasks/telegram_bot.py`; backend reiniciado e `/telegram/status` indicou `running=true`, `last_error=null`. **Ainda falta teste real no chat autorizado** de /status, /task, /cancel, /pause, /resume, /screenshot e /see.
- SwiftUI, Keychain, AppIntents, WidgetKit e CI iOS Simulator existem no repositório, mas estão explicitamente deferidos. CI de build iOS/WidgetKit passou no run 40198612123.
- Segurança: não ativar Tailscale Funnel nem vincular backend a 0.0.0.0; não expor token em logs, commits ou mensagens.

## Testes conhecidos
- Suite completa depois da correção do fallback de síntese: `pytest -q -rxX` — **1.129 passed, 9 skipped, 31 xfailed, 1 warning, 3.231 subtests** (261,91 s).
- Suite mobile/Telegram/API: **41 passed, 1 warning** (`tests/test_telegram_bot.py tests/test_remote_api_auth.py tests/test_remote_access.py`).
- Suite de regressão fallback/roteamento/auth: **53 passed**.
- Scripts PowerShell parseados; restart real validou API HTTPS autenticada, Telegram running e Ollama 15 modelos.
- Não considerar xfails como passados; continuar triagem e registrar limitações reais.

## Commits recentes
Branch remota sincronizada até `f4662bc9` (docs: record post-restart mobile API validation), após:
- `e85aa7d4` — fix: make MYRA startup safe and reload user config
- `87f2ea0c` — docs: record remote task conflict and cancellation tests
- `ea246cea` — fix: ensure Ollama is ready before starting MYRA
- `3ffee174` — fix: clarify synthesis fallback and preserve tool evidence
- `28ec67cb` — docs Fase 28 (verificar com git log se ainda está no histórico)
Commits devem sempre ser feitos como `BielDominic <gabrielenrique817@gmail.com>`.

## Próximas ações (retomar sem perguntar)
1. Atualizar roadmap para marcar instalação/validação iOS física, TestFlight, Siri/widget/APNs e CarPlay como adiados para a fase final, sem apagar implementação.
2. Começar **Fase 30 — Distribuição Windows**, priorizando pendências verificáveis: teste visual do menu tray, toast nativo, auto-start após reboot real e validação limpa de instalador/upgrade/uninstall. Não criar um arquivo `PHASE30_DISTRIBUTION.md` sem antes procurar docs já existentes.
3. Manter em paralelo as pendências da Fase 26 (recovery tests e xfail triage) e a validação real dos comandos Telegram quando possível.
4. Após cada alteração: testes focados, teste mais amplo quando viável, revisar diff, atualizar roadmap/documento, commit e push usando identidade do usuário.
5. Antes de mexer no Git, verificar branch, status e arquivos não rastreados. Há backups/logs/memória local não rastreados (por exemplo `ROADMAP.md.bak-*`, `agent.py.bak-*`, `logs/`, `tasks/.telegram_chat_first_messages.json`, `tasks/.telegram_chat_memory.json`); preservar e nunca incluí-los em commits.

## Comandos de partida
```powershell
Set-Location C:\computer-agent
git status --short --branch
git log -8 --oneline
.\venv\Scripts\python.exe -m pytest tests\test_telegram_bot.py tests\test_remote_api_auth.py tests\test_remote_access.py -q
```

## Como saber que está 100%
Não declarar fase/projeto concluído apenas porque testes automatizados passaram. Exigir testes reais nos fluxos aplicáveis, registrar dependências externas (Apple Developer/APNs/dispositivo), manter os itens adiados explicitamente pendentes e calcular progresso global com base no roadmap atualizado.
