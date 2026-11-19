# MYRA — Instalação com um clique (Windows)

## Requisitos
- Windows 10/11 x64.
- Internet para integrações externas e, opcionalmente, para instalar Ollama e baixar pesos de modelos.
- O runtime Python, dependências core, wheelhouse de visão/ML e Chromium já acompanham o instalador. Os pacotes opcionais de visão são instalados somente após escolha do usuário.

## Instalação
1. Abra [MYRA Releases](https://github.com/BielDominic/myra-agent/releases).
2. Baixe `MYRA_0.26.3_x64-setup.exe`.
3. Execute o instalador. Ele prepara o backend local e o workspace individual da conta Windows.
4. Abra MYRA pelo menu Iniciar.
5. Na primeira execução, a tela **Bem-vindo à MYRA / Primeiros passos** permite selecionar recursos antes de ativá-los. É possível concluir, salvar as preferências ou adiar.

## O que já vem no instalador
- Python oficial 3.14.10 x64 e dependências core fixadas em wheels offline.
- Chromium compatível com Playwright.
- Pacotes opcionais de ML/visão: PyTorch CPU, TorchVision, OpenCV, ONNX Runtime, RapidOCR, Ultralytics e dependências transitivas. Os wheels são incluídos, mas NÃO instalados por padrão; a ativação é feita pelo usuário na tela Primeiros passos e ocorre offline.
- Backend, ferramentas, tarefas, extensão Chrome, scripts e workspace.
- Nenhum download do PyPI é necessário para o conjunto core ou para ativar o pacote de visão incluído.

## Setup de boas-vindas e escolhas opcionais
A tela **Primeiros passos** aparece na primeira abertura e continua disponível na navegação lateral para alterações futuras.

- **Visão e ML:** escolha “Ativar recursos de visão e ML” para instalar os wheels incluídos (PyTorch CPU, OpenCV, ONNX Runtime, RapidOCR e Ultralytics). Se desmarcar, nenhum desses pacotes será instalado.
- **Ollama:** escolha instalar/configurar para usar o Windows Package Manager (winget). Também é possível abrir o [site oficial do Ollama](https://ollama.com/download).
- **Modelo local:** escolha entre `qwen2.5:3b` (leve, recomendado), `qwen2.5:7b` (maior qualidade e maior consumo de memória), `llama3.2:3b` ou `qwen2.5:1.5b`. O download só ocorre se a opção Ollama estiver marcada e você clicar em Concluir.
- **Adiar:** “Fazer isso depois” libera o workspace sem baixar recursos opcionais. Você pode retornar à tela Primeiros passos quando quiser.

Os pesos do modelo **não estão dentro do EXE**: são baixados pelo Ollama para evitar duplicar gigabytes em cada cópia do instalador. O PyTorch incluído é CPU-only para maior compatibilidade entre computadores.

## Melhorador de prompts
No chat, o botão **Melhorar prompt** usa o modelo local configurado para reescrever o pedido com objetivos, restrições e critérios de sucesso mais claros. O texto aprimorado volta ao campo de mensagem para revisão; não é enviado automaticamente. É necessário ter um modelo de chat disponível.

## Espaço de trabalho por usuário
Cada conta do Windows mantém seus próprios dados em `%LOCALAPPDATA%\\MYRA`, incluindo:
- `workspace\\projects`, `workspace\\downloads`, `workspace\\artifacts` e `workspace\\memory`.
- `chrome_profile` e `config\\user_profile.json`.
- `config\\model.json`, quando um modelo é configurado.

Os dados não são compartilhados entre contas Windows diferentes. O instalador não conecta o usuário ao computador do desenvolvedor nem envia o workspace ao GitHub.

## Diagnóstico
- Backend: http://127.0.0.1:8000
- Estado do setup: `GET http://127.0.0.1:8000/setup/status` (somente local).
- Logs: `%LOCALAPPDATA%\\MYRA\\logs`.
- Reexecute `%LOCALAPPDATA%\\MYRA\\setup_backend.ps1` para reparar o ambiente.
- Ollama e modelos podem ser gerenciados pela aba Modelos ou pela tela Primeiros passos.
