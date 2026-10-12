# Changelog

Este arquivo segue o formato [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Datas em ISO 8601. O histórico abaixo resume mudanças identificáveis nos commits recentes do repositório; não pretende substituir o histórico Git completo.

## [Unreleased]

### Added
- Documentação de retomada de contexto, inventário de ferramentas e arquitetura do sistema.

### Changed
- Roadmap atualizado para refletir a conclusão da FASE 25 e o avanço do foco para a FASE 26.

### Fixed
- Registo das ferramentas visuais no planner documentado como parte do ciclo de integração da FASE 25.

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
