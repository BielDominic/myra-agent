# FASE 28.2 — Controle Telegram da MYRA

## Estado

Codigo implementado, desativado ate que o usuario configure token e chat IDs e faca uma validacao real no Telegram.

## Decisao de arquitetura

A integracao usa **long polling**, nao webhook. Assim, o PC inicia conexoes de saida para a API do Telegram; nao precisa abrir uma porta publica nem publicar o backend FastAPI na internet. Tailscale continua opcional para acesso direto a outros endpoints locais, mas nao e necessario para o bot funcionar.

## Configuracao

1. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather) e copie o token.
2. Envie `/start` ao bot e descubra o seu `chat_id` usando `getUpdates` na API do Telegram antes de ligar o polling.
3. Defina as variaveis de ambiente no Windows (nao coloque segredos no repositorio):

```powershell
[Environment]::SetEnvironmentVariable("MYRA_TELEGRAM_BOT_TOKEN", "<TOKEN_DO_BOT>", "User")
[Environment]::SetEnvironmentVariable("MYRA_TELEGRAM_ALLOWED_CHAT_IDS", "<SEU_CHAT_ID>", "User")
```

Aceita varios IDs separados por virgula. Reinicie o backend; o bot inicia automaticamente somente se **as duas variaveis** estiverem configuradas. Para verificar, consulte `GET /telegram/status`. Tambem existem `POST /telegram/start` e `POST /telegram/stop`.

Para obter o chat ID, depois de mandar uma mensagem ao bot, abra `https://api.telegram.org/bot<TOKEN_DO_BOT>/getUpdates` no navegador local. Nao compartilhe essa URL: ela contem o token.

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

## Pendencias de validacao

- Criar bot e configurar token/chat ID no computador do usuario.
- Testar /status, /task, /cancel, /pause, /resume, /screenshot e /see com o Telegram real.
- Configurar Tailscale separadamente se for necessario acesso direto ao backend/widget fora da rede local.
- App iOS nativo e widgets iOS permanecem fora desta entrega.
