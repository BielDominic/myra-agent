# Changelog

Este arquivo segue o formato [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Datas em ISO 8601. O histórico abaixo resume mudanças identificáveis nos commits recentes do repositório; não pretende substituir o histórico Git completo.

## [Unreleased]

### Fixed
- **Segurança — path traversal nas rotas de ficheiros:** o guard usava `os.path.abspath(destino).startswith(os.path.abspath(WORKSPACE_DIR))`, que aceita prefixos irmãos (`..\workspace_evil\x`) e permitia ler, escrever, mover e apagar ficheiros fora do workspace. Substituído por `agent.caminho_no_workspace()`, que usa `os.path.commonpath` (7 pontos de uso: list_dir, read_file, write_file, delete_file, create_dir, move_file, code_run_file).
- **Robustez — unicode no stdout:** imprimir um emoji (ex.: nome de ficheiro vindo do planner) levantava `UnicodeEncodeError` com a consola cp1252 e derrubava a rota com HTTP 500. `stdout`/`stderr` passam a ser reconfigurados para UTF-8 com `errors="replace"` no arranque do `agent.py`.

### Added
- `tests/helpers.py` — infraestrutura dos testes severos: `AmbienteIsolado`, `workspace_temporario`, `sem_rede`, `HTTPFalso`, `cliente_agent`.
- `tests/test_seguranca_paths.py` — 20 testes severos de contenção de caminhos (travessia, prefixo irmão, caminho absoluto, unicode/emoji, entradas degeneradas).

## [2026-10-15]

### Added
- **FASE 26 — verificacao:** `tasks/autonomy.py::verificar()` decide se o objetivo foi atingido com base em evidencia observavel; sem evidencia o resultado e `indeterminado` e o sucesso nunca e declarado.
- **FASE 26 — recuperacao:** `tasks/autonomy.py::recuperar()` sugere nova estrategia por ferramenta, mantem acoes bloqueadas por assinatura e aplica limites explicitos (`MAX_TENTATIVAS_POR_ACAO`, `LIMITE_RECUPERACOES`).
- **FASE 26 — persistencia:** `tasks/task_store.py` (SQLite, `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3`, configuravel por `MYRA_TASK_DB`) grava objetivo, passo atual, historico, estado, timestamps e eventos de auditoria.
- **FASE 26 — pausa/retomada:** rotas `POST /task_pause`, `POST /task_resume`, `GET /task_pendentes` e `GET /task_detalhe/{task_id}`; `retomar_task()` continua do passo seguinte preservando historico, observacoes, verificacoes e recuperacoes.
- **FASE 26 — retomada apos crash:** no startup o agent marca como `interrompido` as tasks `em_execucao` de execucoes anteriores (comparacao por `run_id`) e permite retoma-las.
- Testes em `tests/` (43 testes, `unittest` da biblioteca padrao): persistencia, verificacao, recuperacao, ciclo completo, pausa/retomada, retomada apos crash, cancelamento e rotas HTTP.

### Changed
- `executar_task()` aceita `task_id`, `historico`, `passo_inicial` e `persistir`, devolve `task_id` e `motivo_encerramento` e passa a ter os estados `pausado` e `falhou`.
- O planner recebe `DIRETRIZ DE RECUPERACAO` e `ACOES BLOQUEADAS`; o loop recusa `finalizar` quando existe evidencia forte de falha (no maximo 2 recusas).
- `tasks/cancel_state.py` controla tambem a pausa (`marcar_pausada`, `resetar_pausa`, `esta_pausada`).
- `MAX_ERROS_CONSECUTIVOS` deriva de `LIMITE_RECUPERACOES + 1` para que o motivo explicito da recuperacao seja o que encerra a task.
- Roadmap: FASE 26 em progresso (80%), progresso declarado 72%.

## [2026-10-12]

### Added
- **FASE 25 concluída — visão com coordenadas:** módulo `computer/vision_locate.py` com fuzzy matching e fallback LLM.
- Rotas `/vision_locate`, `/vision_click` e `/vision_type` no backend.
- Três ferramentas visuais integradas em `tools/browseragent.py` e regras de seleção no planner.

### Changed
- O planner recebeu instruções para escolher as ferramentas `vision_*` quando precisa localizar ou interagir com elementos visíveis sem seletor DOM.
- Roadmap bilingue atualizado: FASE 25 concluída; progresso declarado em 70%; próxima fase ativa é a 26.

### Fixed
- Remoção de duplicação das rotas visuais após patch repetido, conforme commit `dddac46`.
- Polling da extensão Chrome serializado com `setTimeout` recursivo e guarda `pollRunning`, evitando acumulação de polls.
- Estado de conclusão/cancelamento de tarefas ligado ao widget, conforme commits recentes.

## [2026-10-11]

### Added
- README de projeto com arquitetura, setup, grupos de ferramentas, segurança e troubleshooting.
- Melhorias do widget Tauri para passos, tema, modo compacto, bloqueio e cancelamento real de tarefas.
- Ferramenta de pesquisa Google visível na extensão/bridge.

### Changed
- Polling da bridge alterado para execução serializada e menos atrasos de scroll.

### Fixed
- Correções no ciclo de polling para evitar múltiplas execuções concorrentes.
- Melhorias no cancelamento real de tasks e na comunicação de estado para o widget.

## Histórico de commits de referência

- `8bc41fc` — `feat(vision): vision_* no tools/browseragent + regras no planner`
- `dddac46` — `feat(vision): rotas /vision_locate, /vision_click, /vision_type + planner`
- `12e9871` — `feat(vision): vision_locate com fuzzy match + LLM fallback`
- `0220841` — `merge: ROADMAP bilingue com badges`
- `b33061b` — `docs: roadmap completo bilingue (PT/EN) com badges, fases 25-31`
- `2a97ef` — `merge: README profissional + widget + cancelamento de tasks`
- `e7a5875` — `feat(widget): bloco A (passos, tema, compacto, trava, pausa UI) + cancelamento real de tasks`
- `7103b03` — `feat(bridge): browser_search_google_visivel + fix polling serializado`
- `67f47ac` — `fix(offscreen): polling serializado com setTimeout recursivo + guarda pollRunning`
