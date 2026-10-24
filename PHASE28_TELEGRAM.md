# FASE 28.2 — Controle Telegram da MYRA

## Estado

Codigo implementado; token e allowlist estao configurados neste PC. A validacao ao vivo esta bloqueada por HTTP 409 (outro poller getUpdates); o codigo agora para ao detectar o conflito e impede reinicio concorrente do thread. Reiniciar o backend e confirmar `/telegram/status` ainda sao necessarios.

## Decisao de arquitetura

A integracao usa **long polling**, nao webhook. Assim, o PC inicia conexoes de saida para a API do Telegram; nao precisa abrir uma porta publica nem publicar o backend FastAPI na internet. Tailscale continua opcional para acesso direto a outros endpoints locais, mas nao e necessario para o bot funcionar.

## Configuracao

**Preferencial:** execute o assistente local que pede o token sem exibi-lo, valida o bot e encontra chats a partir das mensagens recentes:

```powershell
cd C:\computer-agent
powershell -ExecutionPolicy Bypass -File .\scripts\setup_telegram.ps1
```

Antes, crie/regenere o token em [@BotFather](https://t.me/BotFather), abra o bot no Telegram e envie `/start`. O script solicita o token com entrada oculta, permite escolher o chat ID autorizado e grava `MYRA_TELEGRAM_BOT_TOKEN` e `MYRA_TELEGRAM_ALLOWED_CHAT_IDS` no ambiente do usuario do Windows. Depois, reinicie o backend.

Alternativamente, configure as variaveis manualmente no Windows. Nunca coloque o token em arquivos versionados, comandos salvos, logs ou mensagens.

Aceita varios IDs separados por virgula. Reinicie o backend; o bot inicia automaticamente somente se **as duas variaveis** estiverem configuradas. Para verificar, consulte `GET /telegram/status`. Tambem existem `POST /telegram/start` e `POST /telegram/stop`.

**Seguranca:** se um token foi colado em uma conversa ou outro local compartilhado, revogue-o no @BotFather e use um novo antes de ativar o bot. Evite abrir URLs da API contendo o token em navegadores ou compartilhar capturas delas.

## Comandos

- `/task <objetivo>` — executa uma tarefa; objetivo limitado a 1.200 caracteres.
- `/status` — estado, objetivo e passo atual.
- `/cancel` — solicita cancelamento.
- `/pause` — pausa no proximo ponto seguro.
- `/resume <task_id>` — retoma uma tarefa persistida.
- `/screenshot` — envia uma captura da tela sob demanda.
- `/see [pergunta]` — pede uma descricao da tela ao modelo visual.
- `/help` — mostra a ajuda.

A tarefa roda em uma thread separada para que o bot continue recebendo `/status` e `/cancel`.

## Seguranca

- Sem token ou allowlist, o bot nao inicia.
- Somente IDs em `MYRA_TELEGRAM_ALLOWED_CHAT_IDS` podem executar comandos; outros chats sao ignorados.
- Token e IDs nao sao escritos nos logs nem incluidos nas respostas de status.
- Capturas de tela so sao enviadas quando `/screenshot` e solicitado.
- O bot usa o backend local em `127.0.0.1:8000`; nao deve ser exposto publicamente.
- O token nunca deve ser commitado ou colocado em arquivos versionados.

## Diagnostico de polling duplicado (2026-10-24)

- O endpoint real `/telegram/status` informou `HTTP 409 Conflict: terminated by other getUpdates request`.
- `getMe` confirmou que o token atual e valido; `getWebhookInfo` confirmou que nao ha webhook configurado. A inspecao local encontrou apenas um backend MYRA ativo, por isso nao e possivel afirmar se o outro poller esta noutro processo/PC ou se houve uma corrida anterior de start/stop.
- O polling agora para ao receber 409, em vez de repetir a requisicao a cada 3 segundos; `start()` tambem recusa criar um segundo thread enquanto o anterior ainda esta encerrando.
- A alteracao requer reiniciar o backend para entrar em vigor. Depois, consultar `/telegram/status`. Se o 409 persistir, localizar e parar a outra instancia que usa o mesmo token; nao revogar o token automaticamente.

## Pendencias de validacao

- Criar bot e configurar token/chat ID no computador do usuario.
- Testar /status, /task, /cancel, /pause, /resume, /screenshot e /see com o Telegram real.
- Configurar Tailscale separadamente se for necessario acesso direto ao backend/widget fora da rede local.
- App iOS nativo e widgets iOS permanecem fora desta entrega.
