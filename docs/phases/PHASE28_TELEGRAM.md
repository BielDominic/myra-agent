# FASE 28.2 — Controle Telegram da MYRA

## Estado

Codigo implementado; token e allowlist estao configurados neste PC. Em 2026-10-25, o backend foi reiniciado como processo Uvicorn unico vinculado a `127.0.0.1` (em vez do modo `python agent.py` com processo supervisor e worker). Depois do restart, `/telegram/status` confirmou `running=true` e `last_error=null`, sem novo HTTP 409 observado. A entrega de comandos reais ainda precisa ser validada pelo chat autorizado.

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

## Diagnostico de polling duplicado (2026-10-24 a 2026-10-25)

- Antes do restart, `/telegram/status` informou `HTTP 409 Conflict: terminated by other getUpdates request`.
- A verificacao dos processos encontrou o launcher `python agent.py` e seu processo servidor; a inicializacao pelo script `abrir_tudo.ps1` usa `python agent.py`, enquanto `start.ps1` usa Uvicorn diretamente.
- Para evitar o modo multiprocesso nesse caminho de execucao, o servidor foi reiniciado com `python -m uvicorn agent:app --host 127.0.0.1 --port 8000`. Tambem foi corrigido o bloco `if __name__ == '__main__'` para usar `127.0.0.1`.
- Depois do restart, `/telegram/status` confirmou `running=true` e `last_error=null`, sem novo 409 observado; `netstat` confirmou que a API escuta apenas em `127.0.0.1:8000`.
- Continuar monitorando o estado e validar os comandos reais a partir do chat autorizado. Nao revogar o token automaticamente.

## Pendencias de validacao

- Testar `/status`, `/task`, `/cancel`, `/pause`, `/resume`, `/screenshot` e `/see` com o Telegram real e confirmar os resultados no chat autorizado.
- Tailscale esta instalado/conectado no PC, mas nao ha peer iOS no tailnet; adicionar o iPhone para acesso direto.
- O app iOS possui fontes SwiftUI e projeto Xcode inicial em `mobile-ios/`; build CI, execucao em dispositivo e widgets/Siri/notificacoes ainda precisam de validacao/implementacao.


## Imagens no Telegram (2026-11-20)

- Geracao local: mensagens naturais como `Gere uma imagem de ...`, `Quero uma imagem de ...`, `Me mande uma imagem de ...` e `Pode gerar uma imagem de ...` sao reconhecidas e enfileiradas em background. `/image` e `/imagine` continuam disponiveis.
- Entrega: a imagem gerada e validada como PNG/JPEG/WEBP e enviada como foto real pela Bot API `sendPhoto`; nao e devolvido apenas um link local.
- Recepcao: fotos e documentos de imagem enviados ao chat autorizado sao baixados do Telegram e encaminhados ao endpoint visual local com a legenda/pergunta.
- Edicao: legendas com instrucoes explicitas (por exemplo, `Edite a foto`, `Mude o fundo`, `Remove the background`) acionam `/images/edit` local e devolvem o resultado como foto via `sendPhoto`; analises sem pedido de edicao continuam no modelo visual.
- Geracao e edicao compartilham a mesma fila de VRAM, evitando concorrencia no ComfyUI.
- Diagnostico: falhas de upload preservam a descricao devolvida pelo Telegram, para que erros de tamanho/formato/limite nao fiquem escondidos atras de uma mensagem generica.
- Hardware: ComfyUI local `127.0.0.1:8188`, checkpoint DreamShaper 8, GPU RTX A2000 4 GB com low-VRAM. A fila serializa geracoes para evitar concorrencia de VRAM.

### Validacao em 2026-11-20

- [x] `/images/status` confirmou ComfyUI e checkpoint local disponiveis.
- [x] Geracao real de imagem 512x512 retornou HTTP 200 e PNG valido.
- [x] `sendPhoto` real aceito pelo Telegram para a lista autorizada.
- [x] Fluxo completo de linguagem natural -> ComfyUI -> `sendPhoto` executado com sucesso no chat autorizado.
- [x] 79 testes de `tests/test_telegram_bot.py` passaram, incluindo parser conversacional, entrega de fotos e roteamento de edicao local.
- [ ] Validar recebimento e edicao de uma foto real enviada pelo usuario no chat autorizado.


## Atualizacao ? edicao de fotos no Telegram (2026-11-20)

- Legendas com intencao explicita de edicao sao reconhecidas em portugues e ingles.
- A foto e baixada do Telegram e enviada ao endpoint local `/images/edit` (ComfyUI img2img).
- A resposta editada e devolvida como foto real via `sendPhoto`, nao como URL.
- Fotos sem legenda de edicao continuam sendo analisadas pelo modelo visual.
- Documentos enviados com MIME `image/*` tambem entram no mesmo fluxo.
- Geracao e edicao compartilham a fila de VRAM.
- 79 testes focados passaram; falta validar uma foto real enviada pelo chat autorizado.
