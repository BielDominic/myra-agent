# FASE 28.3 — Fundacao do app iOS MYRA

## Entrega atual

Esta fase entrega a primeira camada de acesso remoto autenticado, fontes SwiftUI e um projeto Xcode inicial (`mobile-ios/MyraMobile.xcodeproj`). O app ainda **nao foi compilado nem executado** localmente: este PC e Windows e nao possui Xcode. O workflow `.github/workflows/ios-mobile-build.yml` faz a validacao e compilacao para iOS Simulator num runner macOS; o resultado do CI deve ser confirmado antes de declarar o build aprovado.

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

Os arquivos em `mobile-ios/MyraMobile/` fornecem:

- tela de conexao e status;
- envio de tarefas e cancelamento;
- atualizacao de status a cada 5 segundos;
- token salvo no Keychain do iOS;
- URL remota HTTPS obrigatoria (HTTP so e permitido para localhost durante desenvolvimento).

Para compilar: num Mac com Xcode, crie um projeto iOS App SwiftUI (iOS 17+) chamado `MyraMobile`, adicione `MyraMobileApp.swift`, `ContentView.swift` e `RemoteAPI.swift ao target, e execute primeiro no Simulator. Depois configure o endpoint MagicDNS HTTPS do Tailscale terminado em `/remote/v1` e o token gerado no Windows.

## Pendencias de validacao

- [ ] Criar/validar o projeto Xcode e compilar no macOS.
- [ ] Confirmar que o endpoint Serve so encaminha `/remote/v1` e nao a raiz da API.
- [ ] Testar status, tarefa e cancelamento no iPhone via Tailscale.
- [ ] Implementar Face ID/biometria, notificacoes, widgets iOS e Siri Shortcuts em fases posteriores.
