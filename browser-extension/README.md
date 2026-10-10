# MYRA Browser Bridge (protótipo)

Esta extensão é a primeira etapa para usar abas do Chrome já abertas e autenticadas, sem copiar o perfil para `C:\\chrome-debug` nem iniciar um segundo Chrome.

## Estado atual

**Protótipo isolado; ainda não está conectado ao planner do `agent.py`.** O popup permite testar leitura de texto da aba ativa, navegação e clique por texto. A integração com o planner exige endpoints autenticados no backend e registro de ferramentas em `tasks/simple_task.py`; não declare a extensão como integração completa até isso estar implementado e testado.

## Instalar para teste local

1. Abra `chrome://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem compactação**.
4. Selecione a pasta `browser-extension` deste repositório.
5. Abra uma página de teste não sensível e clique no ícone da extensão.
6. Teste **Ler aba ativa**, **Navegar na aba atual** e **Clicar por texto**.

## Segurança

- Não lê nem exporta cookies, senhas, tokens de sessão ou local storage.
- A API configurada é limitada a `localhost` / `127.0.0.1`.
- Não use inicialmente em banco, pagamentos ou ações irreversíveis.
- As permissões de leitura/execução são amplas o suficiente para operar na aba ativa; mantenha a extensão desabilitada quando não estiver testando.
- Login, CAPTCHA, MFA e bloqueios do site continuam sob controle do site; a extensão não os contorna.
- Este protótipo não contém polling de comandos nem endpoints de execução remota.

## Próxima etapa de integração

Implementar no backend uma fila de comandos local com token de uso local, endpoints de claim/complete, limites de timeout e confirmação explícita para ações sensíveis. Depois, registrar ferramentas `browser_read_active_tab`, `browser_navigate_active_tab` e `browser_click_text` no planner. Não exponha esses endpoints à rede local ou pública.
