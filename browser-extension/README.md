# MYRA Browser Bridge

Extensão Chrome Manifest V3 e fila local de comandos para permitir que o planner do MYRA opere em uma aba-alvo do Chrome do usuário. A extensão usa APIs oficiais do Chrome e não lê cookies, senhas, tokens de sessão nem local storage de sites.

## 1. Configure o backend

No PowerShell do Windows, gere um token aleatório e guarde-o em um gerenciador de senhas:

```powershell
$bytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$token = -join ($bytes | ForEach-Object { $_.ToString("x2") })
[Environment]::SetEnvironmentVariable("MYRA_BROWSER_BRIDGE_TOKEN", $token, "User")
Write-Host $token
```

Feche e reinicie o terminal/processo que inicia `agent.py` para que ele leia a variável de ambiente. Não publique o token em issues, commits, screenshots ou mensagens.

Se o MYRA estiver rodando como serviço ou iniciado por outro shell, configure a variável nesse mesmo ambiente e reinicie o processo.

## 2. Carregue a extensão

1. Abra `chrome://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione a pasta `browser-extension` do repositório.
5. Abra o popup da extensão, cole o token gerado, marque **Habilitar integração automática** e clique **Salvar e conectar**.
6. Confirme a permissão do Chrome para acessar páginas HTTP/HTTPS quando o navegador perguntar. A extensão não injeta scripts em todos os sites em segundo plano; o acesso amplo é opcional e solicitado só quando você habilita a integração.
7. Deixe o Chrome aberto enquanto testa o planner.

## 3. Como a aba-alvo é escolhida

- Se a aba ativa for uma página normal HTTP/HTTPS, MYRA usa essa aba.
- Se a aba ativa for o Open WebUI local em `localhost:8080`, `127.0.0.1:8080` ou `[::1]:8080`, MYRA ignora essa interface e seleciona a página HTTP/HTTPS mais recentemente acessada na mesma janela do Chrome.
- Se não houver outra página web elegível, MYRA retorna um erro explicativo em vez de ler o texto do próprio comando.
- A mesma seleção é aplicada à leitura, navegação e clique.

## 4. Ferramentas do planner

- `browser_read_active_tab()`: devolve título, URL e texto visível da aba-alvo (até 12.000 caracteres).
- `browser_read_active_tab(url_contains="github.com")`: procura em todas as janelas do Chrome uma aba cuja URL contenha esse trecho, sem diferenciar maiúsculas/minúsculas. Se várias abas corresponderem, lê a mais recentemente acessada. O trecho pode ser domínio, parte do caminho ou outro fragmento da URL; não precisa incluir o protocolo.
- Se `url_contains` não for informado, mantém o comportamento padrão: usa a aba ativa ou, se ela for o Open WebUI, a página web mais recentemente acessada na mesma janela.
- Se nenhuma aba corresponder a `url_contains`, retorna um erro claro e não lê outra aba por engano.
- `browser_navigate_active_tab(url)`: navega a aba-alvo para uma URL HTTP/HTTPS.
- `browser_click_text(text)`: clica em um botão/link visível com texto exato.

Os comandos expiram após 40 segundos se a extensão não responder. Teste em páginas não sensíveis antes de usar em contas autenticadas. Não use clique automático para confirmar pagamentos, excluir dados, enviar mensagens ou outras ações irreversíveis sem confirmação explícita do usuário.

## Segurança e limitações

- Os endpoints da extensão exigem `MYRA_BROWSER_BRIDGE_TOKEN` no cabeçalho `X-MYRA-BRIDGE-TOKEN` e rejeitam clientes não locais.
- Configure a variável de ambiente antes de iniciar o backend. Sem ela, a API do bridge permanece indisponível.
- A API principal do MYRA tem outras rotas preexistentes; este bridge não altera sua configuração de rede global.
- A extensão não contorna login, MFA, CAPTCHA, bloqueios anti-automação ou permissões do site.
- O service worker do Chrome pode ser suspenso pelo navegador. Se a ferramenta expirar, abra o popup e confirme que a integração está habilitada.
- Este commit foi criado pelo GitHub API e não foi executado no seu PC. Faça teste manual após atualizar o checkout e recarregar a extensão.
