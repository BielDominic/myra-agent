# MYRA — Handoff de Contexto

- **Última atualização:** 2026-10-12
- **Progresso declarado no roadmap:** ~70%
- **Branch de referência:** `main`
- **Último commit conhecido antes desta atualização:** `8bc41fc`
- **Roadmap:** [ROADMAP.md](ROADMAP.md)
- **Arquitetura:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Inventário de ferramentas:** [TOOLS.md](TOOLS.md)
- **Histórico de mudanças:** [CHANGELOG.md](CHANGELOG.md)

> O percentual é uma estimativa de projeto, não uma métrica automatizada de testes. Consulte os critérios e o estado por fase no roadmap.

## Resumo executivo

MYRA é um agente pessoal de IA local-first para Windows. Combina FastAPI, um modelo local via Ollama, ferramentas de navegador, extensão Chrome Manifest V3 com bridge persistente em SQLite, controles desktop, visão local e interface Open WebUI. O planner adaptativo escolhe ferramentas passo a passo, observa os resultados retornados e pode tentar novamente dentro do limite de passos.

O commit `8bc41fc` adicionou as ferramentas `vision_locate`, `vision_click` e `vision_type` à integração `tools/browseragent.py` e regras no planner. O teste end-to-end reportado confirmou a sequência `vision_locate` → coordenadas → `vision_click`. A FASE 25 (Visão com Coordenadas) foi marcada como concluída no roadmap em 2026-10-12. A FASE 26 é o próximo foco: ciclo autónomo completo com observação, verificação, recuperação e persistência.

## O que funciona hoje (por área)

### Backend e planner
- FastAPI em `agent.py`, com rotas para ferramentas e integração compatível com OpenAI em `/v1/chat/completions`.
- `/task_simple` executa o planner adaptativo de `tasks/simple_task.py`.
- Estado de tarefa, cancelamento e eventos são expostos por rotas como `/task_status`, `/task_cancel` e `/task_events`.
- O planner regista ferramentas estruturadas, ferramentas do browser bridge e ferramentas visuais.

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

1. **FASE 26 — ciclo autónomo:** observar após cada ação, verificar o objetivo, recuperar de falhas, persistir estado e retomar tarefas após crash.
2. **FASE 27 — overlay visual TARS:** janela transparente click-through, cursor/trajectória visível, highlight do alvo, estados visuais e eventos em tempo real.
3. **Estabilidade e testes:** testes automatizados para planner, bridge, ferramentas visuais e fluxos de erro; logs estruturados e health checks.
4. **Browser/Computer Use:** melhorar recuperação de navegação, pop-ups inesperados, iFrames/shadow DOM, drag-and-drop, clipboard, múltiplos monitores e verificação pós-ação.
5. **Persistência e observabilidade:** histórico consultável e tarefas sobrevivendo a reinícios.
6. **Ferramentas avançadas:** anexos de e-mail, documentos PDF/Office, YouTube sem legendas, scheduler, voz e integrações externas.
7. **Segurança e distribuição:** permissões explícitas, auditoria, sandbox de código, instalador, auto-start, notificações e documentação de instalação.

Consulte [ROADMAP.md](ROADMAP.md) para a lista completa de fases e checkboxes. Não considere uma funcionalidade concluída apenas por estar listada: confirme a implementação e faça um teste relevante.

## Próximos passos — FASE 26: ciclo autónomo

1. Inspecionar `tasks/simple_task.py`, `computer/vision_locate.py`, as rotas de estado/eventos e o estado atual da branch.
2. Definir contratos claros para observação, verificação e recuperação (entradas, saídas e estados de erro).
3. Implementar observação após cada ação, começando por screenshot + resultado estruturado.
4. Implementar verificação do objetivo com evidência observável, evitando declarar sucesso sem confirmação.
5. Implementar recuperação limitada: nova estratégia, limite de tentativas e motivo explícito para falha.
6. Persistir task ID, objetivo, passo atual, histórico, estado e timestamps em SQLite; testar retoma após reinício.
7. Ligar pausa/continuação ao estado persistido sem perder o contexto.
8. Criar testes unitários e end-to-end para sucesso, alvo não encontrado, timeout, cancelamento e reinício.
9. Só depois integrar o ciclo no overlay da FASE 27.

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
2. Leia, nesta ordem: `README.md`, `ROADMAP.md`, este `HANDOFF.md`, `tasks/simple_task.py`, `computer/vision_locate.py`, `agent.py`.
3. Confirme que `vision_locate`, `vision_click` e `vision_type` estão registadas e que as rotas correspondentes existem.
4. Execute os testes relevantes disponíveis no checkout e confirme serviços/portas antes do teste end-to-end.
5. Comece pela FASE 26; não avance para o overlay avançado antes de haver um ciclo observe → act → verify → recover fiável.
6. Atualize o roadmap e este handoff somente após verificar mudanças reais.
