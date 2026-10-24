# FASE 27.5 — Integracao REA

## Estado

Integracao inicial concluida; ponte MCP em validacao. Em 2026-10-24, a raiz permitida foi configurada de forma persistente no ambiente do usuario do Windows, e a analise real de `C:\computer-agent\widget-tauri\ui` executou com sucesso usando `MYRA_REA_ALLOWED_ROOTS=C:\computer-agent` configurado para o processo de validacao. A saida JSON foi limitada a 12.000 caracteres, conforme o limite de seguranca; a configuracao persistente no ambiente de deploy ainda precisa ser confirmada.

## O que foi adicionado

- `tasks/rea_tools.py`: ferramentas `rea_status`, `rea_catalog`, `rea_analyze_javascript`, `rea_mcp_list_tools` e `rea_mcp_call`.
- `tools/rea_mcp_bridge.mjs`: cliente baseado no SDK oficial MCP para conectar ao servidor REA por stdio.
- Descoberta real confirmou 207 ferramentas no servidor; a MYRA expõe os nomes/descricoes do catalogo e os esquemas JSON de 11 ferramentas explicitamente permitidas para leitura.
- `rea_mcp_call` rejeita ferramentas fora da allowlist, argumentos que nao sejam objeto JSON e payloads acima de 16.000 caracteres; para `analyze_javascript_application`, tambem valida que o caminho exista e esteja dentro de uma raiz autorizada.
- Validacao real: a chamada MCP `analyze_javascript_application` analisou `C:\\computer-agent\\workspace\\rea_smoke_test` e retornou Evidence com `status=ok`, sem truncamento. A ferramenta `current_document` exige que exista um alvo aberto num provedor binario e devolveu `target_unavailable` quando nenhum estava aberto.
- Registro das ferramentas no planner da MYRA.
- Regras no prompt para restringir o uso a software proprio ou explicitamente autorizado.
- O pacote REA nao e instalado globalmente. O `npx` usa a versao fixada `rea-agents@6.5.0` apenas quando a analise for chamada.
- A analise exige uma pasta existente de app JavaScript/Electron e verifica se o caminho esta dentro de uma raiz permitida.
- Nenhum comando do REA e executado automaticamente no startup.

## Requisitos e configuracao

- Node.js suportado pelo REA: 22.19+, 24.11+ ou 26+.
- O padrao de raiz permitida e `C:\computer-agent\workspace`.
- Para permitir outras pastas, defina `MYRA_REA_ALLOWED_ROOTS` com uma lista separada por ponto e virgula no Windows, por exemplo:

```powershell
[Environment]::SetEnvironmentVariable(
  "MYRA_REA_ALLOWED_ROOTS",
  "C:\computer-agent\workspace;D:\Projetos",
  "User"
)
```

Reinicie o backend depois de alterar variaveis de ambiente. O pacote REA sera baixado do npm na primeira analise; isso exige internet naquele momento, mas nao instala um pacote global.

## Como usar

No planner da MYRA, solicite a analise de uma aplicacao JavaScript/Electron que esteja dentro de uma raiz autorizada. Tambem e possivel chamar `rea_status` para verificar Node/npx e as raizes configuradas.

## Seguranca e limites

- Use apenas software proprio ou com autorizacao explicita.
- A ferramenta nao aceita caminhos fora das raizes permitidas.
- A chamada usa argumentos separados, sem `shell=True`.
- O processo tem timeout de 240 segundos e a resposta e limitada a 12.000 caracteres.
- O comando integrado e o analisador estatico de aplicacoes JavaScript; nao configura Hopper/Ghidra/IDA nem instala motores nativos.

## Referencias

- https://github.com/morluto/rea
- https://www.npmjs.com/package/rea-agents
