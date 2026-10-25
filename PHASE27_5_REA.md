# FASE 27.5 - Integracao REA

## Estado

**Concluida no escopo de integracao e validacao funcional (2026-10-25).** A ponte MCP, a allowlist de leitura, a analise JavaScript e a inspecao estatica de binarios foram testadas. O provedor Ghidra 12.1.4 tambem foi instalado e validado com operacoes reais de instrucao, nome de endereco e resolucao de chamadas em um PE x64 de teste. O executavel real da MYRA passou pela analise estatica Go/Rust; a analise completa do Ghidra para esse executavel maior excedeu o prazo de analise do provedor e nao e declarada como aprovada.

## Implementacao

- `tasks/rea_tools.py`: ferramentas `rea_status`, `rea_catalog`, `rea_analyze_javascript`, `rea_mcp_list_tools` e `rea_mcp_call`.
- `tools/rea_mcp_bridge.mjs`: cliente MCP pelo SDK oficial; localiza dinamicamente `rea-agents@6.5.0` no cache npx ou aceita `MYRA_REA_PACKAGE_ROOT`, valida a versao e nao depende de um hash de cache codificado.
- Descoberta real: 207 ferramentas no servidor. A MYRA expoe os nomes/descricoes do catalogo e os esquemas JSON de 15 ferramentas explicitamente permitidas para leitura.
- `rea_mcp_call` bloqueia ferramentas fora da allowlist, argumentos que nao sejam objeto JSON e payloads acima de 16.000 caracteres. Os caminhos sao canonizados e precisam estar em uma raiz autorizada; a analise JavaScript tambem verifica a existencia e o tipo do alvo.
- A ponte restaura o alvo binario validado nas chamadas seguintes, porque cada invocacao cria uma nova sessao MCP.
- A ponte encaminha somente variaveis de ambiente necessarias e explicitamente permitidas para o processo REA. Isso corrige o filtro padrao do SDK MCP, que nao encaminhava `JAVA_HOME`/`GHIDRA_INSTALL_DIR`; outras variaveis do processo, inclusive possiveis segredos, nao sao copiadas indiscriminadamente.
- O planner da MYRA registra as ferramentas e restringe o uso a software proprio ou explicitamente autorizado.
- O pacote REA nao e instalado globalmente; `npx` usa a versao fixada `rea-agents@6.5.0` quando uma ferramenta e chamada.
- Nenhuma analise e executada automaticamente no startup.

## Validacao real (2026-10-25)

- `node --check tools/rea_mcp_bridge.mjs`: aprovado.
- `python -m pytest tests/test_rea_tools.py tests/test_rea_routing.py -q`: **18 passed** apos as correcoes de seguranca, roteamento e timeout MCP.
- Descoberta MCP: 207 ferramentas encontradas; somente 15 esquemas da allowlist expostos.
- Analise real de `C:\\computer-agent\\widget-tauri\\ui`: `status=ok`, Evidence JSON dentro do limite de 12.000 caracteres.
- `open_binary` no `myra-widget.exe`: `status=ok`, formato PE, arquitetura x86_64, SHA-256 `d7475410841660b45b00e463d9beca1f52f606a0931da87e0a1089b66720ff1e`.
- `inspect_go_binary` e `inspect_rust_binary` no executavel real da MYRA: ambos `status=ok`, sem executar o alvo.
- Ghidra 12.1.4 + Eclipse Temurin JDK 21.0.12.1 instalados em `C:\\tools`; `GHIDRA_INSTALL_DIR`, `JAVA_HOME` e `REA_ANALYSIS_PROVIDER=ghidra` persistidos no ambiente do usuario.
- Validacao ponta a ponta pela API real da MYRA (2026-10-25): o planner enviou `tool_name=inspect_native_instruction` com `address` como argumento direto; a normalizacao produziu chamada MCP valida e o Ghidra retornou Evidence para `where-smoke-test.exe`, endereco `0x140001000`, bytes `cc`, mnemonic `INT3`, comprimento 1 e provedor `ghidra` 12.1.4. SHA-256 do fixture: `f51fab8041e5023d7290b540a2106f051ef0bd2bc3443c9daf318628b560fa29`.
- Os argumentos REA achatados pelo planner agora sao normalizados de forma deterministica; argumentos repetidos entre o objeto `arguments` e campos diretos sao rejeitados antes de invocar o servidor. Ferramentas Ghidra demoradas recebem timeout explicito e limitado (240 s para a chamada MCP; limite total do subprocesso Python de 260 s).
- Smoke test Ghidra em um PE x64 de 64 KiB: `inspect_native_instruction`, `address_name` e `resolve_native_call_targets` retornaram Evidence com `status=ok` e identificaram o provedor Ghidra 12.1.4.
- `current_document`, `current_address` e `current_procedure` sao operacoes de cursor da integracao GUI do Hopper; o provedor Ghidra nao as declara. No Windows, Hopper nao e suportado. Isso e uma limitacao por provedor, nao uma falha da analise Ghidra.
- A analise completa do `myra-widget.exe` pelo Ghidra excedeu o prazo de analise do provedor. Nao marcamos essa execucao como aprovada; a inspecao estatica Go/Rust do mesmo arquivo foi aprovada. Para investigacoes Ghidra detalhadas desse binario grande, pode ser necessario reduzir o alvo/escopo ou usar um perfil de analise mais leve.

## Configuracao e seguranca

Raizes permitidas persistidas para o usuario Windows:

- `C:\\computer-agent\\workspace`
- `C:\\computer-agent\\widget-tauri\\ui`
- `C:\\computer-agent\\widget-tauri\\src-tauri\\target\\release`

Para adicionar/remover raizes, altere `MYRA_REA_ALLOWED_ROOTS` no ambiente do usuario e reinicie o backend. O pacote REA requer Node.js 22.19+, 24.11+ ou 26+. Nao ha `shell=True`; argumentos sao enviados como lista; a saida e limitada a 12.000 caracteres; as ferramentas de mutacao e execucao permanecem fora da allowlist.

## Como usar

No planner da MYRA, solicite a analise de uma aplicacao JavaScript/Electron ou de um binario local dentro de uma das raizes autorizadas. `rea_status` verifica Node/npx e as raizes configuradas; `rea_mcp_list_tools` mostra o catalogo e a allowlist de leitura.

## Referencias

- https://github.com/morluto/rea
- https://www.npmjs.com/package/rea-agents
