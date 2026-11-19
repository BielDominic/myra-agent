# FASE 28 — Controle Mobile da MYRA

**Estado (2026-10-25): Tailscale Serve HTTPS ativo somente para `/remote/v1`; status autenticado retorna 200, sem Bearer retorna 401 e rotas fora do prefixo retornam 404. Tarefas remotas reais, conflito concorrente HTTP 409 e cancelamento foram validados via HTTPS; o cancelamento levou o estado a `idle`. Ollama local recuperado e sintese LLM normal confirmada. App assinado/APNs, validacao no iPhone real e comandos Telegram reais continuam pendentes.**

## Arquitetura

- **Telegram:** long polling iniciado pelo PC; nao exige webhook, porta publica ou API FastAPI exposta. Comandos protegidos por allowlist `MYRA_TELEGRAM_ALLOWED_CHAT_IDS`.
- **Cliente mobile direto:** endpoints separados sob `/remote/v1`, autenticados com `Authorization: Bearer <token>`.
- **Executor:** as tarefas sao executadas pelo backend local da MYRA no PC Windows.
- **Rede privada:** Tailscale e o caminho previsto para o app iOS; nao usar Funnel nem publicar a raiz inteira da API.

## Implementado no repositorio

- [x] Diagnostico local Tailscale em `tasks/remote_access.py` e `GET /remote_access/status`, sem listar outros peers nem publicar a API.
- [x] Telegram em `tasks/telegram_bot.py`, com allowlist, long polling, comandos `/task`, `/status`, `/cancel`, `/pause`, `/resume`, `/screenshot`, `/see`, `/tasks`, `/taskinfo`, `/ping`, `/models`, `/model`, `/newchat` e `/help`.
- [x] Tratamento de HTTP 409 no polling: para a instancia local em vez de repetir conflitos indefinidamente.
- [x] API remota Bearer em `tasks/remote_api_auth.py` e rotas `GET /remote/v1/status`, `POST /remote/v1/task`, `POST /remote/v1/cancel`.
- [x] API remota desativada com HTTP 503 quando o processo nao tem `MYRA_REMOTE_API_TOKEN`; token incorreto/ausente recebe HTTP 401.
- [x] Limites de payload: objetivo de 1 a 1.200 caracteres e `max_passos` de 1 a 50; tarefa duplicada retorna HTTP 409. Validacao real via HTTPS/Tailscale (2026-10-25): segunda tarefa concorrente rejeitada com HTTP 409; `POST /remote/v1/cancel` retornou sucesso e status subsequente confirmou `idle`; objetivo vazio e `max_passos=51` foram rejeitados com HTTP 422.
- [x] Corrigido o bind do servidor iniciado por `python agent.py`: agora usa `127.0.0.1`, nao `0.0.0.0`. Backend reiniciado e confirmado por `netstat` escutando somente em loopback.
- [x] Scaffold SwiftUI em `mobile-ios/MyraMobile/`, incluindo status, envio/cancelamento de tarefa, HTTPS fora de localhost e token no Keychain.
- [x] Projeto Xcode em `mobile-ios/MyraMobile.xcodeproj`; o app e os AppIntents Siri passaram no build macOS em 2026-10-25.
- [x] AppIntents Siri para enviar tarefa e consultar estado, usando o mesmo endpoint HTTPS e token do Keychain.
- [x] WidgetKit Home Screen/Lock Screen implementado em `mobile-ios/MyraWidgetExtension/`, mostrando apenas estado/progresso e horario da ultima atualizacao.
- [x] App Group `group.com.myra.mobile` configurado nos entitlements do app e da extensao; exige registro na conta Apple Developer para uso assinado.
- [x] Workflow macOS em `.github/workflows/ios-mobile-build.yml` compila app e extensao iOS Simulator sem assinatura; o target WidgetKit foi confirmado no CI (run 40198612123, sucesso).
- [x] Script `scripts/setup_remote_api.ps1` para gerar token aleatorio de 256 bits e guarda-lo no ambiente do usuario Windows; mostra o segredo uma vez para ser guardado manualmente.
- [x] Suite direcionada em 2026-10-25: `pytest tests/test_telegram_bot.py tests/test_remote_api_auth.py tests/test_remote_access.py -q` — **41 passed, 1 warning**. Reexecutada apos validar concorrencia/cancelamento remoto: **41 passed, 1 warning**.
- [x] Suite completa apos ajuste do fallback de sintese: `pytest -q -rxX` — **1.129 passed, 9 skipped, 31 xfailed, 1 warning e 3.231 subtests** (261,91s).
- [x] Regressao de fallback do planner: quando o LLM de sintese falha, a resposta identifica explicitamente a indisponibilidade da sintese e preserva as evidencias reais da ferramenta; suite direcionada `test_rea_routing.py`, `test_chat_routing.py` e `test_remote_api_auth.py`: **53 passed**.
- [x] Diagnostico do teste remoto: o Ollama local nao estava em execucao, causando `URLError` na sintese final. Ollama foi iniciado novamente; `/api/tags` respondeu, geracao direta com `qwen2.5:3b-instruct-q5_K_M` passou e uma segunda tarefa remota via HTTPS concluiu com sintese do LLM e evidencia da janela Notepad visivel.
- [x] Recuperacao de inicializacao: criado `scripts/ensure_ollama.ps1` e integrado a `abrir_tudo.ps1` e `iniciar_myra.ps1`. Parse PowerShell passou nos scripts; teste de recuperacao confirmou reinicio do Ollama e 15 modelos disponiveis.
- [x] Seguranca dos scripts de startup: `scripts/stop_myra_backend.ps1` encerra apenas processos Python identificados como backend MYRA e aborta se a porta 8000 pertencer a outro processo; removida a pratica perigosa de matar todos os processos Python. `scripts/import_user_environment.ps1` recarrega configuracoes do escopo User sem imprimir segredos. Teste de reinicializacao de `iniciar_myra.ps1` confirmou API HTTPS autenticada funcionando, Telegram `running=true`/`last_error=null` e Ollama com 15 modelos. Uma tarefa remota adicional apos o restart chegou a `done`, abriu a Calculadora e produziu sintese LLM normal.

## Bloqueios e validacoes externas pendentes

- [x] Resolvido o HTTP 409 do Telegram ao reiniciar o backend em processo unico Uvicorn vinculado a loopback; `/telegram/status` foi confirmado com `running=true` e `last_error=null` apos o restart.
- [ ] Testar com o Telegram real `/status`, `/task`, `/cancel`, `/pause`, `/resume`, `/screenshot` e `/see`, verificando os resultados recebidos e nao apenas respostas simuladas.
- [x] Instalar o cliente Tailscale 1.104.2 no Windows; o estado agora e `Running` e o PC recebeu IPv4 Tailscale.
- [x] Adicionar/autenticar o iPhone no mesmo tailnet. Validado em 2026-10-25: peer `iphone181` (iOS) online em `100.112.204.30`; `tailscale ping` respondeu via DERP(lhr) em ~106-129 ms.
- [x] Gerar token aleatorio de 256 bits e salva-lo no ambiente de usuario Windows; reiniciar o backend para carregar o segredo. Validado em 2026-10-25: `GET /remote/v1/status` retorna HTTP 200 com Bearer correto e HTTP 401 sem token. O segredo nao foi escrito no repositorio nem exibido nos logs.
- [x] Configurar Tailscale Serve com HTTPS para encaminhar exclusivamente `/remote/v1` a `http://127.0.0.1:8000/remote/v1`, sem Funnel nem portas publicas. Validado em 2026-10-25: `/remote/v1/status` com Bearer correto retorna HTTP 200; sem token retorna HTTP 401; `/`, `/telegram/status`, `/remote_access/status`, `/openapi.json` e `/docs` retornam HTTP 404 pelo hostname Tailscale.
- [x] Confirmar o build do target WidgetKit no workflow macOS `ios-mobile-build.yml`; build completo aprovado no run 40198612123 em 2026-10-25.
- [ ] Registrar o App Group `group.com.myra.mobile` na conta Apple Developer e testar a extensao assinada.
- [ ] Implementar/validar notificacoes APNs push; exigem Team ID, chave APNs e registro do dispositivo, que nao estao configurados neste ambiente.
- [ ] Testar no iPhone status, envio de tarefa, conflito de tarefa em execucao, cancelamento, Siri, widget e reconexao apos perda de rede. Validacao PC-side em 2026-10-25: duas tarefas via HTTPS/Tailscale abriram Calculadora e Notepad e chegaram a `done` com UI Automation; uma tarefa de controle confirmou concorrencia HTTP 409 e cancelamento com transicao a `idle`. O Ollama foi reiniciado apos estar parado, geracao local passou e a segunda tarefa concluiu com sintese LLM normal. Isso nao substitui o teste no iPhone real.

## Como validar localmente

```powershell
Set-Location C:\\computer-agent
.\\venv\\Scripts\\python.exe -m pytest tests\\test_telegram_bot.py tests\\test_remote_api_auth.py tests\\test_remote_access.py -q
.\\venv\\Scripts\\python.exe -m pytest tests\\test_remote_api_auth.py -q
```

Para diagnosticar sem revelar segredos, consulte `GET http://127.0.0.1:8000/telegram/status` e `GET http://127.0.0.1:8000/remote_access/status`. Nunca registre o token Telegram ou o token remoto em logs, arquivos versionados ou mensagens.

## Seguranca

- O backend permanece vinculado a `127.0.0.1:8000`; confirmado por `netstat` em 2026-10-25 e por teste TCP negativo em `100.127.243.80:8000` (`TcpTestSucceeded=False`). O acesso remoto passa exclusivamente pelo Tailscale Serve HTTPS no caminho `/remote/v1`.
- O token remoto nao e habilitado automaticamente pelo script; e preciso reiniciar o backend para aplicar a variavel de ambiente.
- O Tailscale Serve esta configurado e confirmado por `tailscale serve status --json`; o unico handler configurado e `/remote/v1` -> `http://127.0.0.1:8000/remote/v1`. Revalidar a restricao se a configuracao Serve mudar.
- Nenhum segredo foi adicionado ao repositorio.
