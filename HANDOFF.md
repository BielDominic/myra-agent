# MYRA — Handoff de Contexto

- **Última atualização:** 2026-10-15
- **Progresso declarado no roadmap:** ~72%
- **Branch de referência:** `main`
- **Último commit conhecido antes desta atualização:** `4dddd09e`
- **Roadmap:** [ROADMAP.md](ROADMAP.md)
- **Arquitetura:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Inventário de ferramentas:** [TOOLS.md](TOOLS.md)
- **Histórico de mudanças:** [CHANGELOG.md](CHANGELOG.md)

> O percentual é uma estimativa de projeto, não uma métrica automatizada de testes. Consulte os critérios e o estado por fase no roadmap.

## Resumo executivo

MYRA é um agente pessoal de IA local-first para Windows. Combina FastAPI, um modelo local via Ollama, ferramentas de navegador, extensão Chrome Manifest V3 com bridge persistente em SQLite, controles desktop, visão local e interface Open WebUI. O planner adaptativo escolhe ferramentas passo a passo, observa os resultados retornados e pode tentar novamente dentro do limite de passos.

O commit `8bc41fc` adicionou as ferramentas `vision_locate`, `vision_click` e `vision_type` à integração `tools/browseragent.py` e regras no planner. A FASE 25 (Visão com Coordenadas) foi marcada como concluída em 2026-10-12. A FASE 26 (Ciclo Autónomo Completo) está **em progresso a 80%**: observação textual (`computer/observer.py`), verificação de objetivo e recuperação de falhas (`tasks/autonomy.py`), persistência de tasks em SQLite (`tasks/task_store.py`), pausa/retomada (`/task_pause`, `/task_resume`) e retomada após crash estão implementadas e cobertas por 43 testes automatizados. A validação end-to-end com Ollama real (`qwen2.5:7b`) foi executada em 2026-10-15 (conclusão por evidência do observer, falha com motivo explícito e pausa/retomada com contexto preservado); falta a observação com screenshot e a validação com o navegador em uso real.

## O que funciona hoje (por área)

### Backend e planner
- FastAPI em `agent.py`, com rotas para ferramentas e integração compatível com OpenAI em `/v1/chat/completions`.
- `/task_simple` executa o planner adaptativo de `tasks/simple_task.py`.
- Estado de tarefa, cancelamento e eventos são expostos por rotas como `/task_status`, `/task_cancel` e `/task_events`.
- **FASE 26:** `POST /task_pause` pausa no próximo ponto seguro e persiste o estado; `POST /task_resume` (body `{"task_id": "..."}`, opcional `max_passos`) retoma em background; `GET /task_pendentes` lista tasks retomáveis; `GET /task_detalhe/{task_id}` devolve histórico + eventos de auditoria.
- O planner regista ferramentas estruturadas, ferramentas do browser bridge e ferramentas visuais.

### Ciclo autónomo (FASE 26)
- `computer/observer.py::observar` avalia cada ação (resultado da ferramenta + LLM local) e devolve `sucesso`, `objetivo_atingido`, `motivo` e `proximo_passo_sugerido`. É uma avaliação textual: não tira screenshot.
- `tasks/autonomy.py::verificar` só declara sucesso com evidência (`sucesso=True` e `objetivo_atingido=True`); caso contrário devolve `False` (evidência negativa) ou `None`/`indeterminado` e o planner decide.
- `tasks/autonomy.py::recuperar` gera a diretriz de nova estratégia, bloqueia assinaturas de ações que falharam e aplica limites (`MAX_TENTATIVAS_POR_ACAO=2`, `LIMITE_RECUPERACOES=3`). Falhas esgotadas encerram a task com `status="falhou"` e motivo explícito.
- `executar_task` recusa `finalizar` quando há evidência forte de falha (máximo 2 recusas) e encerra em vez de declarar sucesso falso.
- `tasks/task_store.py` persiste objetivo, passo atual, histórico, estado, timestamps e eventos em `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3` (`MYRA_TASK_DB` redireciona, útil em testes). No startup, tasks `em_execucao` de execuções anteriores passam a `interrompido` e podem ser retomadas.
- Testes: `python -m unittest discover -s tests -t .` (43 testes; não chamam LLM, rede nem ferramentas reais).

### Navegador
- Ferramentas Playwright legadas para abrir URLs, pesquisar, ler páginas, clicar, digitar, navegar para trás e esperar.
- Extensão Chrome MV3 conectada ao backend pelo bridge.
- Bridge usa uma fila SQLite local para enfileirar comandos, entregá-los à extensão e receber resultados.
- Ferramentas do bridge incluem leitura de separadores/página, navegação, pesquisa, digitação, cliques por texto, scroll e fechar/abrir separadores.

### Visão
- Serviço de visão local `llm-eyes` configurado separadamente.
- Rotas `/screenshot` e `/see` para captura/análise, conforme configuração.
- FASE 25: `computer/vision_locate.py` implementa localização por descrição com fuzzy matching e fallback LLM; `/vision_locate`, `/vision_click` e `/vision_type` estão registadas no planner.
- A localização visual não deve ser tratada como garantia universal: validar resultado e coordenadas em runtime.

### Desktop / PC
- Ferramentas para mover/clicar o mouse, duplo clique, clique direito, digitar, pressionar teclas, hotkeys, scroll, screenshot, listar janelas, obter janela ativa e focar janela.
- A cobertura de automação de aplicações e a recuperação de ações continuam em desenvolvimento.

### Email, arquivos e utilitários
- Gmail IMAP/SMTP: listar, ler, pesquisar, enviar, responder, marcar lido/não lido, mover e excluir mensagens.
- Ferramentas de workspace: listar, ler, escrever, excluir, criar pastas, mover e pesquisar arquivos.
- Utilitários: hora atual, notas, clima e execução Python, conforme configuração.
- Confirme destinatários e conteúdo antes de enviar e-mails; operações destrutivas exigem cuidado.

### YouTube, código e visualização
- YouTube: transcrição, resumo, perguntas, guardar/listar/ler transcrições; pesquisa estruturada de vídeos e canais recentes.
- CodeAgent: gerar, explicar, analisar, revisar, refatorar, otimizar, converter, criar testes/documentação, SQL/regex, scaffolding, lint, métricas, dependências, execução e benchmark de código.
- `tools/visuals_core.py`: ferramentas de tabelas, comparação, gráficos, heatmaps, timelines, fluxogramas e árvores para saída textual/HTML.

### Interface e infraestrutura
- Open WebUI para chat; Docker e proxy local conforme configuração.
- Widget Tauri com modos de visualização, personalidade e estado da tarefa.
- Ollama para inferência local; visão servida separadamente.
- Portas padrão documentadas: FastAPI 8000, visão 8081, Ollama 11434, Open WebUI/proxy 8082 ou mapeamento configurado.

## O que falta (priorizado)

1. **FASE 26 — restante:** observação com screenshot dedicado (hoje é textual) e validação com o navegador/extensão em uso real; pausa, retomada, recuperação e retomada após crash já foram validadas com Ollama real em 2026-10-15.
2. **FASE 27 — overlay visual TARS:** janela transparente click-through, cursor/trajectória visível, highlight do alvo, estados visuais e eventos em tempo real (o SSE `/task_events` já existe e a pausa é sinalizada por `passo_atual="PAUSADO (...)"`).
3. **Estabilidade e testes:** ampliar a cobertura para planner/bridge reais, logs estruturados e health checks.
4. **Browser/Computer Use:** melhorar recuperação de navegação, pop-ups inesperados, iFrames/shadow DOM, drag-and-drop, clipboard, múltiplos monitores e verificação pós-ação.
5. **Persistência e observabilidade:** histórico consultável pela interface (as rotas `/task_pendentes` e `/task_detalhe` já existem) e limpeza automática de tasks antigas.
6. **Ferramentas avançadas:** anexos de e-mail, documentos PDF/Office, YouTube sem legendas, scheduler, voz e integrações externas.
7. **Segurança e distribuição:** permissões explícitas, auditoria, sandbox de código, instalador, auto-start, notificações e documentação de instalação.

Consulte [ROADMAP.md](ROADMAP.md) para a lista completa de fases e checkboxes. Não considere uma funcionalidade concluída apenas por estar listada: confirme a implementação e faça um teste relevante.

## Próximos passos — FASE 26 (restante) e FASE 27

1. Rodar os testes: `python -m unittest discover -s tests -t .` (devem passar 43).
2. Validar as rotas novas no servidor em execução (depois de reiniciar o agent, porque as rotas `/task_*` novas só existem no código atualizado): `POST /task_pause`, `GET /task_pendentes`, `POST /task_resume`, `GET /task_detalhe/{task_id}`.
3. Testar a retomada após reinício do processo: matar o agent no meio de uma task, subir de novo e confirmar que a task aparece como `interrompido` em `/task_pendentes` e retoma pelo `/task_resume`.
4. Adicionar screenshot ao observer (FASE 26 restante) e validar alvo não encontrado/timeout com o navegador real.
5. Só depois integrar o ciclo no overlay da FASE 27.
6. Atualizar roadmap e este handoff somente após verificar mudanças reais.

## Regras críticas do projeto

- Não commitar segredos, tokens, passwords, cookies, perfis autenticados ou conteúdo privado de e-mail.
- Não expor serviços locais à rede pública sem autenticação, firewall e revisão de segurança.
- Usar branches para desenvolvimento normal; fazer commits pequenos e focados. A referência pedida para este handoff é `main`, mas confirme a branch local antes de alterar código.
- Ler o código e a configuração atuais antes de assumir que README/roadmap refletem o checkout.
- Preservar UTF-8 e evitar alterações não relacionadas.
- Testar sintaxe e comportamento; um teste de sintaxe não substitui teste end-to-end.
- Tratar resultados de modelos e visão como incertos. Verificar ações antes de afirmar sucesso.
- Confirmar ações com consequências reais, especialmente envio de e-mail, exclusão, execução de código e operações autenticadas.
- Restringir execução de código e acesso a arquivos a workspaces confiáveis.
- Não assumir que o projeto está universalmente offline: navegação, pesquisa, YouTube, clima e e-mail exigem rede.

## Como retomar

1. Abra o repositório e confirme a branch/commit:
   ```powershell
   git status
   git branch --show-current
   git log -5 --oneline
   ```
2. Leia, nesta ordem: `README.md`, `ROADMAP.md`, este `HANDOFF.md`, `tasks/simple_task.py`, `tasks/autonomy.py`, `tasks/task_store.py`, `computer/observer.py`, `agent.py`.
3. Confirme que `vision_locate`, `vision_click` e `vision_type` estão registadas, que as rotas `/vision_*` existem e que as rotas `/task_pause`, `/task_resume`, `/task_pendentes` e `/task_detalhe/{task_id}` respondem.
4. Execute `python -m unittest discover -s tests -t .` (43 testes, sem LLM/rede) e confirme serviços/portas antes do teste end-to-end.
5. Valide a FASE 26 com serviços reais (Ollama + browser); só depois avance para o overlay da FASE 27.
6. Atualize o roadmap e este handoff somente após verificar mudanças reais.
