\# 🔧 MYRA — Guia de Reinstalação Completa



> Guia passo-a-passo para reconstruir o MYRA do zero em uma máquina Windows.

> Última atualização: 03/10/2026



\---



\## 📋 Índice



1\. \[Hardware necessário](#1-hardware-necessário)

2\. \[Software base](#2-software-base)

3\. \[Estrutura de pastas](#3-estrutura-de-pastas)

4\. \[Instalação do Python + venv](#4-instalação-do-python--venv)

5\. \[Instalação do Ollama + modelos](#5-instalação-do-ollama--modelos)

6\. \[Containers Docker](#6-containers-docker)

7\. \[Configuração do nginx](#7-configuração-do-nginx)

8\. \[Configuração do agent.py](#8-configuração-do-agentpy)

9\. \[Configuração do Open WebUI](#9-configuração-do-open-webui)

10\. \[Tool BrowserAgent](#10-tool-browseragent)

11\. \[System Prompt do Local Agent](#11-system-prompt-do-local-agent)

12\. \[Testes finais](#12-testes-finais)

13\. \[Backup e restauração](#13-backup-e-restauração)

14\. \[FASE 17 — CodeAgent](#14-fase-17--codeagent)

15\. \[Scripts de inicialização](#15-scripts-de-inicialização)

16\. \[Fases do projeto](#16-fases-do-projeto)



\---



\## 1. Hardware necessário



| Componente | Mínimo | Recomendado |

|---|---|---|

| CPU | Intel i5 / AMD Ryzen 5 | Intel i7-11850H |

| RAM | 8 GB | 16 GB |

| GPU | NVIDIA com 4 GB VRAM | NVIDIA RTX A2000 |

| Disco | 30 GB livres | 50 GB livres |

| SO | Windows 10/11 64-bit | Windows 11 |



\---



\## 2. Software base



Instalar na ordem:



1\. \*\*Python 3.14.x\*\* — https://www.python.org/downloads/

&#x20;  - Marcar "Add Python to PATH"

2\. \*\*Docker Desktop\*\* — https://www.docker.com/products/docker-desktop/

3\. \*\*Ollama\*\* — https://ollama.com/download

4\. \*\*NVIDIA CUDA v12\*\* (⚠️ NÃO v13 — crashava)

5\. \*\*Git\*\* (opcional)



\---



\## 3. Estrutura de pastas



C:\\computer-agent

├── agent.py # Servidor FastAPI

├── agent\_backup\_\*.py # Backups

├── iniciar\_myra.ps1 # Sobe backend

├── iniciar\_visao.ps1 # Sobe visão

├── REINSTALACAO.md # Este guia

├── venv\\ # Ambiente virtual

├── computer\\ # Automação do PC

│ ├── controller.py # Mouse/teclado

│ ├── screen.py # Screenshot

│ └── windows.py # Janelas

├── workspace

│ └── code\\ # Código do CodeAgent

├── screenshots

├── chrome\_profile

├── llm-eyes

│ └── models

│ ├── Qwen3.5-0.8B-UD-Q4\_K\_XL.gguf

│ └── mmproj-F16.gguf

└── webui-custom\\





\---



\## 4. Instalação do Python + venv



```powershell

cd C:\\computer-agent

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m pip install --upgrade pip

python -m pip install fastapi uvicorn\[standard] playwright requests

python -m pip install pyautogui mss pygetwindow PyQt5 pillow

playwright install chromium



&#x20;Sempre usar python -m pip (nunca pip sozinho).



5\. Instalação do Ollama + modelos

powershell

ollama pull qwen2.5:7b                     # Modelo principal

ollama pull qwen2.5:3b                     # Fallback leve

ollama pull llama3.1:8b                    # Alternativo

ollama pull R4C3R/qwen2.5-coder-3b-heretic:latest   # CodeAgent (primário)

ollama pull qwen2.5-coder:7b               # CodeAgent (fallback)



Usar qwen2.5:7b no MYRA (o 3b alucina).



6\. Containers Docker

Open WebUI Custom

powershell

docker run -d `

&#x20; --name open-webui-custom `

&#x20; --restart unless-stopped `

&#x20; -p 8080:8080 `

&#x20; -v open-webui-custom-data:/app/backend/data `

&#x20; ghcr.io/open-webui/open-webui:main

Nginx (myra-proxy)

Criar pasta e config (ver seção 7):



powershell

mkdir C:\\computer-agent\\nginx-conf

docker run -d `

&#x20; --name myra-proxy `

&#x20; --restart unless-stopped `

&#x20; -p 8082:80 `

&#x20; -v C:\\computer-agent\\nginx-conf:/etc/nginx/conf.d `

&#x20; --link open-webui-custom:open-webui-custom `

&#x20; nginx:alpine

Acesso

MYRA via proxy: http://localhost:8082



MYRA direto: http://localhost:8080



7\. Configuração do nginx

Arquivo: C:\\computer-agent\\nginx-conf\\default.conf



nginx

server {

&#x20;   listen 80;

&#x20;   server\_name localhost;



&#x20;   location / {

&#x20;       proxy\_pass http://open-webui-custom:8080;

&#x20;       proxy\_set\_header Host $host;

&#x20;       proxy\_set\_header X-Real-IP $remote\_addr;

&#x20;       proxy\_set\_header X-Forwarded-For $proxy\_add\_x\_forwarded\_for;

&#x20;       proxy\_set\_header X-Forwarded-Proto $scheme;

&#x20;       proxy\_set\_header Accept-Encoding "";



&#x20;       proxy\_http\_version 1.1;

&#x20;       proxy\_set\_header Upgrade $http\_upgrade;

&#x20;       proxy\_set\_header Connection "upgrade";



&#x20;       proxy\_buffering off;

&#x20;       proxy\_cache off;

&#x20;       proxy\_read\_timeout 3600s;

&#x20;       proxy\_send\_timeout 3600s;



&#x20;       sub\_filter\_once off;

&#x20;       sub\_filter '<title>Open WebUI</title>' '<title>MYRA</title>';

&#x20;       sub\_filter '</head>' '<script>(function(){function fix(){var t=document.querySelector("title");if(t\&\&t.textContent!=="MYRA"){t.textContent="MYRA";}document.querySelectorAll("\*").forEach(function(el){if(el.children.length===0\&\&el.textContent\&\&el.textContent.indexOf("(Open WebUI)")!==-1){el.textContent=el.textContent.replace(/\\s\*\\(Open WebUI\\)/g,"");}});}new MutationObserver(fix).observe(document.documentElement,{childList:true,subtree:true,characterData:true});setInterval(fix,200);})();</script></head>';

&#x20;   }

}

Depois: docker restart myra-proxy



8\. Configuração do agent.py

Variável de ambiente permanente

powershell

\[System.Environment]::SetEnvironmentVariable('OPENWEBUI\_API\_KEY', 'sk-sua-key', 'User')

Depois fecha e abre o PowerShell. Toda janela nova já tem.



Gerar API Key no Open WebUI

http://localhost:8082



Settings → Account → API Keys



Create new API key



Copiar (formato sk-...)



Subir o agent.py

powershell

cd C:\\computer-agent

.\\venv\\Scripts\\Activate.ps1

python agent.py

Esperado: Uvicorn running on http://0.0.0.0:8000



9\. Configuração do Open WebUI

Primeiro acesso em http://localhost:8082



Criar conta de admin



Admin Settings → Authentication → habilitar API Keys



Admin Settings → Connections → adicionar Ollama: http://host.docker.internal:11434



10\. Tool BrowserAgent

Admin Settings → Tools → "+ Create New Tool"



Nome: BrowserAgent



Colar código completo (ver browseragent\_tool.py)



Save



Vinculação: Admin Settings → Models → Local Agent → Tools → marcar BrowserAgent → Save



11\. System Prompt do Local Agent

Cola o System Prompt completo em Admin Settings → Models → Local Agent → System Prompt.



Regras críticas:



REGRA #1: Nunca peça confirmação



REGRA #2: Nunca invente resultados



REGRA #3: Chame a ferramenta, não narre



REGRA #4: Nunca diga "timeout" por conta própria



12\. Testes finais

text

Que horas são?

Liste meus emails

Quais janelas estão abertas?

Mova o mouse para 400, 300

Tire um print da minha tela

Abra o Google

Olhe minha tela e me diga o que vê

Qual a previsão do tempo?

13\. Backup e restauração

Fazer backup

powershell

$data = Get-Date -Format 'yyyyMMdd\_HHmmss'

New-Item -ItemType Directory -Force -Path C:\\computer-agent\\backups | Out-Null

Copy-Item C:\\computer-agent\\agent.py "C:\\computer-agent\\backups\\agent\_$data.py" -Force

docker cp open-webui-custom:/app/backend/data/webui.db "C:\\computer-agent\\backups\\webui\_$data.db"

Copy-Item C:\\computer-agent\\iniciar\_myra.ps1 "C:\\computer-agent\\backups\\iniciar\_myra\_$data.ps1" -Force

Copy-Item C:\\computer-agent\\iniciar\_visao.ps1 "C:\\computer-agent\\backups\\iniciar\_visao\_$data.ps1" -Force

Restaurar SQLite

powershell

docker cp C:\\computer-agent\\backups\\webui\_XXXX.db open-webui-custom:/app/backend/data/webui.db

docker restart open-webui-custom

14\. FASE 17 — CodeAgent

O que é

Tool separada do BrowserAgent que adiciona 21 ferramentas de código ao MYRA.



Modelos

Primário: R4C3R/qwen2.5-coder-3b-heretic:latest



Fallback: qwen2.5-coder:7b



As 21 tools

EXECUÇÃO: code\_run, code\_run\_file, code\_benchmark

ANÁLISE: code\_explain, code\_analyze, code\_review, code\_lint, code\_metrics, code\_dependencies

GERAÇÃO: code\_generate, code\_snippet, code\_scaffold, code\_regex, code\_sql, code\_readme

REFATORAÇÃO: code\_refactor, code\_optimize, code\_convert

TESTES/DOCS: code\_test, code\_document

BÔNUS: code\_diff



Instalação

Admin Settings → Tools → "+ Create New Tool"



Nome: CodeAgent



Colar código completo (ver codeagent\_tool.py no backup)



Save



Admin Settings → Models → Local Agent → Tools → marcar BrowserAgent + CodeAgent



Pasta necessária

powershell

New-Item -ItemType Directory -Force -Path C:\\computer-agent\\workspace\\code

Testes validados

Tool	Teste	Status

code\_generate	fibonacci	✅

code\_run	print(2+2)	✅

code\_test	pytest soma	✅

code\_refactor	list comprehension	✅

code\_convert	→ JavaScript	✅

code\_sql	listar usuários	✅

code\_analyze	SQL injection	✅

code\_regex	CPF	✅

code\_metrics	LOC fatorial	✅

9/21 validadas.



15\. Scripts de inicialização

iniciar\_myra.ps1 (backend)

Sobe o agent.py com auto-limpeza de porta 8000.



iniciar\_visao.ps1 (visão)

Sobe o llama-server com Qwen3.5-0.8B.



Atalhos na área de trabalho

MYRA Backend:



text

powershell.exe -ExecutionPolicy Bypass -NoExit -File "C:\\computer-agent\\iniciar\_myra.ps1"

MYRA Visão:



text

powershell.exe -ExecutionPolicy Bypass -NoExit -File "C:\\computer-agent\\iniciar\_visao.ps1"

Rotina diária

Duplo clique em MYRA Backend



Duplo clique em MYRA Visão



Duplo clique em MYRA (PWA)



Containers com auto-restart

powershell

docker update --restart=unless-stopped open-webui-custom myra-proxy

16\. Fases do projeto

✅ FASE 0-8: base, browser, email, confirmação



✅ FASE 9: nome MYRA via nginx sub\_filter



✅ FASE 10: gerenciar chats (backend)



✅ FASE 15: ferramentas de arquivo avançadas



✅ FASE 16: automação do PC



✅ FASE 17: CodeAgent (21 tools) ← NOVA



✅ FASE 18: apagar emails por busca



✅ FASE 19: guia de reinstalação (este arquivo)



⏸️ FASE 11: botões no chat (pausada)



⬜ FASE 12: geração de imagem



❌ FASE 13: geração de vídeo (inviável)



⬜ FASE 14: TTS + Whisper (voz)



⬜ FASE 15.5: mais ferramentas de arquivo



🚨 Problemas conhecidos

"Porta 8000 em uso"

powershell

Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

Open WebUI 502

powershell

docker restart open-webui-custom

Start-Sleep -Seconds 60

docker restart myra-proxy

"qwen2.5:3b alucina"

Usar sempre qwen2.5:7b.



"pyautogui não instalado"

powershell

python -m pip install pyautogui mss pygetwindow pillow

agent.py truncado

⚠️ Não usar Set-Content ou -replace no PowerShell. Sempre editar no Notepad/VSCode.



Fim do guia. Para dúvidas, consultar o histórico do projeto.



text



\---



\## 🎯 Passo 3 — Salva



\*\*Ctrl+S\*\* no Notepad.



\---



\## 🎯 Passo 4 — Confirma



\*\*No PowerShell:\*\*



```powershell

Get-Item C:\\computer-agent\\REINSTALACAO.md | Select-Object Name, Length, LastWriteTime

Esperado: tamanho > 10.000 bytes.



E confirma que a seção FASE 17 está lá:



powershell

Select-String -Path C:\\computer-agent\\REINSTALACAO.md -Pattern "FASE 17|CodeAgent" | Select-Object -First 3









