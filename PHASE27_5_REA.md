# FASE 27.5 — Integracao REA

## Estado

Implementacao de codigo concluida; validacao real com um projeto JavaScript autorizado ainda pendente.

## O que foi adicionado

- `tasks/rea_tools.py`: ferramentas `rea_status` e `rea_analyze_javascript`.
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
