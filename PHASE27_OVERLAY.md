# FASE 27 — Overlay Visual TARS

## O que foi implementado

- Janela Tauri `overlay` transparente, fullscreen, inicialmente oculta e sempre no topo.
- Click-through nativo por `set_ignore_cursor_events(true)`; a camada visual nao deve consumir cliques da aplicacao abaixo.
- A janela principal controla a visibilidade do overlay pelo comando IPC `set_overlay_visible`.
- `src/overlay.js` conecta ao SSE local `/task_events`; nao usa polling para os eventos do overlay.
- Estado visual para execucao, observacao/pensamento, conclusao e erro.
- Ferramentas visuais `vision_locate`, `vision_click` e `vision_type` publicam o alvo no estado do widget. Click/type esperam brevemente para permitir o highlight antes da acao.
- O cursor ilustrativo e o rastro sao desenhados a partir dos alvos publicados. As coordenadas fisicas sao convertidas para pixels CSS usando `devicePixelRatio`.

## Como validar no Windows

1. Atualize o repositorio para a branch que contem esta fase.
2. Execute o MYRA normalmente e confirme que a janela TARS fica oculta quando nao ha task ativa.
3. Inicie uma task; a faixa de estado deve aparecer sem bloquear cliques na janela abaixo.
4. Execute `/vision_locate` e `/vision_click` com um alvo visivel. O alvo deve ser destacado antes do clique.
5. Cancele a task pelo widget e confirme que o overlay acompanha o estado final.
6. Rode os testes: `python -m unittest tests.test_overlay_contract -v` e verifique o job `tauri-check` no GitHub Actions.

## Limites conhecidos

- O overlay mostra a trajetoria entre coordenadas emitidas pelas ferramentas visuais; ainda nao e um espelhamento continuo do cursor fisico do Windows.
- Coordenadas dependem do screenshot principal do `mss` e do monitor principal. Multi-monitor e cenarios de DPI misto precisam de validacao especifica.
- O CI pode validar sintaxe/compilacao e contratos estaticos, mas nao substitui teste visual ao vivo no PC Windows do utilizador.
- A janela overlay esta deliberadamente click-through; controles interativos devem permanecer no widget principal.

## Arquivos

- `src/overlay.html`, `src/overlay.css`, `src/overlay.js`
- `src-tauri/tauri.conf.json`, `src-tauri/src/lib.rs`
- `agent.py` (eventos de alvo nas ferramentas de visao)
- `tests/test_overlay_contract.py`
