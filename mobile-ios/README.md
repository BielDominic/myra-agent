# MYRA Mobile — iOS

O projeto Xcode esta em `MyraMobile.xcodeproj`. Ele contem o app SwiftUI, integracao Siri via AppIntents e a extensao WidgetKit para Home Screen/Lock Screen. O build precisa ser validado no runner macOS do GitHub Actions; a instalacao assinada em dispositivo requer uma conta Apple Developer e um iPhone registrado.

## Configurar conexao

1. No PC Windows da MYRA, configure o segredo de API com `scripts/setup_remote_api.ps1` e reinicie completamente o backend.
2. Instale e autentique o Tailscale no PC e no iPhone usando o mesmo tailnet.
3. Configure um endpoint Tailscale Serve privado limitado somente ao caminho `/remote/v1`; nunca use Funnel nem exponha a raiz do FastAPI.
4. No app, informe uma URL HTTPS cujo caminho seja **exatamente** `/remote/v1` (por exemplo, `https://nome-do-pc.tailnet-name.ts.net/remote/v1`) e o token remoto.
5. O token e guardado no Keychain. O app e os atalhos Siri rejeitam endpoints HTTP remotos, credenciais embutidas, query strings, fragmentos e caminhos diferentes de `/remote/v1`.
6. Teste primeiro a consulta de estado, depois envio e cancelamento de uma tarefa de baixo risco. Verifique o estado real antes de considerar uma acao concluida.

## Funcionalidades

- Status atualizado periodicamente, envio de tarefa e cancelamento.
- Token Bearer no Keychain do iOS.
- Siri AppIntents para enviar tarefa e consultar estado.
- WidgetKit para Home Screen, Lock Screen e accessory rectangular; nao exibe o texto sensivel da tarefa.
- API remota separada, desativada com HTTP 503 enquanto `MYRA_REMOTE_API_TOKEN` nao estiver configurado no processo backend.

## Limites de validacao

O build sem assinatura pode ser executado pelo workflow `.github/workflows/ios-mobile-build.yml` num runner macOS. Sem Mac/Xcode local, conta Apple Developer, iPhone autenticado no tailnet e credenciais APNs, nao e possivel afirmar que a instalacao fisica, o widget no dispositivo, a Siri ou notificacoes push foram validados ao vivo.
