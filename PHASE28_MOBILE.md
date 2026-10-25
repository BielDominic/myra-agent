# FASE 28 — Controle Mobile da MYRA

**Estado: implementacao local em validacao; integracao real ainda bloqueada por configuracao dos dispositivos.**

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
- [x] Limites de payload: objetivo de 1 a 1.200 caracteres e `max_passos` de 1 a 50; tarefa duplicada retorna HTTP 409.
- [x] Corrigido o bind do servidor iniciado por `python agent.py`: agora usa `127.0.0.1`, nao `0.0.0.0`. Backend reiniciado e confirmado por `netstat` escutando somente em loopback.
- [x] Scaffold SwiftUI em `mobile-ios/MyraMobile/`, incluindo status, envio/cancelamento de tarefa, HTTPS fora de localhost e token no Keychain.
- [x] Projeto Xcode inicial em `mobile-ios/MyraMobile.xcodeproj` incluindo os tres fontes Swift.
- [x] Workflow macOS em `.github/workflows/ios-mobile-build.yml` para validar o projeto e compilar para iOS Simulator sem assinatura; a compilacao CI ainda precisa passar.
- [x] Script `scripts/setup_remote_api.ps1` para gerar token aleatorio de 256 bits e guarda-lo no ambiente do usuario Windows; mostra o segredo uma vez para ser guardado manualmente.
- [x] Suite direcionada: `pytest tests/test_telegram_bot.py tests/test_remote_api_auth.py tests/test_remote_access.py -q` — **40 passed, 1 warning**.
- [x] Suite completa apos as alteracoes: `pytest -q -rxX` — **1.127 passed, 9 skipped, 31 xfailed, 1 warning e 3.231 subtests** (265,77s).

## Bloqueios e validacoes externas pendentes

- [x] Resolvido o HTTP 409 do Telegram ao reiniciar o backend em processo unico Uvicorn vinculado a loopback; `/telegram/status` foi confirmado com `running=true` e `last_error=null` apos o restart.
- [ ] Testar com o Telegram real `/status`, `/task`, `/cancel`, `/pause`, `/resume`, `/screenshot` e `/see`, verificando os resultados recebidos e nao apenas respostas simuladas.
- [x] Instalar o cliente Tailscale 1.104.2 no Windows; o estado agora e `Running` e o PC recebeu IPv4 Tailscale.
- [ ] Adicionar/autenticar o iPhone no mesmo tailnet. A consulta resumida encontrou zero peers, incluindo zero peers iOS.
- [ ] Gerar/guardar `MYRA_REMOTE_API_TOKEN` com `scripts/setup_remote_api.ps1` e reiniciar o backend para que o processo carregue o segredo. No diagnostico atual, o processo ativo nao tem esse token; a API remota permanece desativada com HTTP 503.
- [ ] Configurar Tailscale Serve para encaminhar exclusivamente `/remote/v1`; verificar com testes negativos que a raiz e as rotas locais nao ficam acessiveis pelo tailnet. Nao habilitar Funnel nem abrir portas publicas.
- [ ] Confirmar o build do projeto Xcode no workflow macOS `ios-mobile-build.yml` e executar no Simulator/iPhone. O projeto e o workflow ja existem, mas o build ainda nao foi executado/confirmado.
- [ ] Testar no iPhone status, envio de tarefa, conflito de tarefa em execucao, cancelamento e reconexao apos perda de rede.

## Como validar localmente

```powershell
Set-Location C:\\computer-agent
.\\venv\\Scripts\\python.exe -m pytest tests\\test_telegram_bot.py tests\\test_remote_api_auth.py tests\\test_remote_access.py -q
.\\venv\\Scripts\\python.exe -m pytest tests\\test_remote_api_auth.py -q
```

Para diagnosticar sem revelar segredos, consulte `GET http://127.0.0.1:8000/telegram/status` e `GET http://127.0.0.1:8000/remote_access/status`. Nunca registre o token Telegram ou o token remoto em logs, arquivos versionados ou mensagens.

## Seguranca

- O backend permanece vinculado a `127.0.0.1:8000` por padrao.
- O token remoto nao e habilitado automaticamente pelo script; e preciso reiniciar o backend para aplicar a variavel de ambiente.
- O Tailscale Serve so pode ser configurado depois de confirmar a sintaxe da versao instalada e a restricao ao prefixo `/remote/v1`.
- Nenhum segredo foi adicionado ao repositorio.
