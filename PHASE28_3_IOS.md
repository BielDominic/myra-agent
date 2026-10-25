# FASE 28.3 — Fundacao do app iOS MYRA

## Entrega atual

A fundacao iOS esta em `mobile-ios/MyraMobile.xcodeproj`: app SwiftUI, dois AppIntents Siri e extensao WidgetKit para Home Screen/Lock Screen. O build da app e dos AppIntents passou no runner macOS; a extensao WidgetKit e as entitlements de App Group foram adicionadas depois e ainda precisam passar no CI. Este PC Windows nao possui Xcode, portanto nao foi executada no iPhone real.

### API remota protegida

- `GET /remote/v1/status` — estado resumido da tarefa.
- `POST /remote/v1/task` — inicia uma tarefa em background (objetivo maximo 1.200 caracteres; 1–50 passos).
- `POST /remote/v1/cancel` — solicita cancelamento.
- Todos exigem `Authorization: Bearer <token>`.
- Sem `MYRA_REMOTE_API_TOKEN`, os endpoints retornam HTTP 503 e nao executam comandos.
- Token ausente/invalido retorna HTTP 401. O segredo e comparado com `hmac.compare_digest`, nao e retornado em status nem gravado em logs.

### Configurar o token no Windows

Execute no PowerShell **local do PC da MYRA**:

```powershell
Set-Location C:\computer-agent
powershell -ExecutionPolicy Bypass -File .\scripts\setup_remote_api.ps1
```

O script gera um token criptograficamente aleatorio de 256 bits, guarda-o no ambiente do usuario Windows e mostra o valor uma unica vez. Guarde-o num gestor de senhas e cole-o no app iOS. Se ja existir um token, o script pede confirmacao explicita antes de o substituir; `-Force` tambem pode ser usado quando se deseja rotacionar o token deliberadamente. Reinicie completamente o backend MYRA depois de definir/rotacionar a variavel, pois processos ja iniciados nao recebem automaticamente as mudancas do ambiente. Nunca commit o token nem o envie por chat. Sem token carregado pelo processo, a API permanece desativada com HTTP 503.

### Expor somente a rota autenticada pelo Tailscale

Depois de instalar e autenticar o Tailscale no PC e no iPhone, configure um endpoint Serve **limitado ao caminho** `/remote/v1`, usando o CLI oficial atual. O exemplo de configuracao de path no Tailscale Serve e documentado em https://tailscale.com/docs/reference/tailscale-cli/serve.

Exemplo a validar na versao instalada do Tailscale:

```powershell
tailscale serve --https=443 --set-path=/remote/v1 http://127.0.0.1:8000
tailscale serve status
```

Nao use Tailscale Funnel e nao exponha a raiz do FastAPI: as rotas locais antigas nao fazem parte desta API remota e nao devem ficar acessiveis pelo iPhone. Se o comando/roteamento de path nao corresponder a versao instalada, pare e revise `tailscale serve --help` antes de prosseguir.

### Codigo SwiftUI

Os arquivos e targets em `mobile-ios/` fornecem:

- app SwiftUI com conexao, status, envio e cancelamento;
- polling de status a cada 5 segundos enquanto o app esta ativo;
- token Bearer guardado no Keychain;
- HTTPS obrigatorio para endpoints remotos (HTTP so e permitido em localhost);
- Siri AppIntents para enviar uma tarefa e consultar o estado atual;
- WidgetKit para Home Screen e Lock Screen, mostrando apenas estado e progresso (sem expor o texto da tarefa na tela bloqueada);
- App Group `group.com.myra.mobile` para compartilhar o estado resumido entre app e widget.

Abra `mobile-ios/MyraMobile.xcodeproj` no Xcode (iOS 17+). Para usar o widget em dispositivo assinado, registre `group.com.myra.mobile` na conta Apple Developer e habilite o mesmo App Group para app e extensao. O workflow `.github/workflows/ios-mobile-build.yml` compila o app e a extensao no runner macOS sem assinatura; build da extensao ainda precisa ser confirmado. Configure o endpoint MagicDNS HTTPS do Tailscale terminado em `/remote/v1` e o token gerado no Windows.

## Pendencias de validacao

- [ ] Confirmar o build CI do target WidgetKit no runner macOS.
- [ ] Registrar o App Group `group.com.myra.mobile` na conta Apple Developer e validar assinatura/instalacao.
- [ ] Guardar o token remoto no iPhone e confirmar que o backend foi reiniciado com `MYRA_REMOTE_API_TOKEN`.
- [ ] Autenticar o iPhone no tailnet, configurar Serve limitado a `/remote/v1` e provar que a raiz/rotas locais nao ficam expostas.
- [ ] Testar status, tarefa, cancelamento, Siri e widget no iPhone real via Tailscale.
- [ ] Notificacoes APNs push exigem Apple Developer Team, chave APNs e registro do dispositivo; ainda nao ha credenciais nem endpoint de entrega configurados. Nao declarar push validado antes do teste real.
