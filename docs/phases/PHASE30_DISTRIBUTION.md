# Fase 30 — Distribuição Windows

Atualizado: 2026-10-25  
Branch: `feature/fase26-vision-fixes`

## Escopo

Preparar distribuição confiável do widget MYRA para Windows, sem declarar a fase concluída antes de validar os fluxos no sistema real.

## Validações realizadas

- [x] Build release Tauri x64 concluído.
- [x] Instalador NSIS gerado: `widget-tauri/src-tauri/target/release/bundle/nsis/MYRA_0.1.0_x64-setup.exe` (aprox. 2,43 MiB).
- [x] Testes Rust para comparação do comando de auto-start: 3 aprovados, 0 falhas.
- [x] Smoke test de instalação silenciosa em diretório isolado do usuário: exit code 0; executável e desinstalador presentes.
- [x] Smoke test de desinstalação silenciosa: exit code 0 e diretório de instalação removido.
- [x] Corrigido o hook NSIS de pré-desinstalação para remover a entrada `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\MYRA`, evitando referência obsoleta ao executável após desinstalar; também remove a identidade de notificação da MYRA.

## Ainda pendente

- [ ] Teste visual real do menu da bandeja: Mostrar MYRA, alternância de auto-start e Sair.
- [ ] Teste real de notificação toast no Windows (incluindo identidade/ícone e comportamento com Não Perturbe).
- [ ] Validar auto-start ativado/desativado lendo o registro do usuário e após reinicialização real.
- [ ] Validar upgrade por cima de uma instalação anterior, preservação de preferências e limpeza da versão antiga.
- [ ] Verificar entradas de Aplicativos Instalados/registro e confirmar remoção após desinstalação.
- [ ] Smoke test de inicialização e conectividade com o backend depois da instalação de release.
- [ ] Executar testes Python de regressão do widget e a suíte geral após as alterações.

## Limites dos testes

A instalação/desinstalação silenciosa foi feita em uma pasta temporária exclusiva e removida após o teste; não substituiu a instalação habitual do usuário. Não foi realizada reinicialização física do computador nem afirmado que o menu/toast foi validado visualmente. O hook NSIS foi alterado após o primeiro build e o instalador foi reconstruído com sucesso.

## Próxima sequência

1. Executar testes de regressão Python e confirmar o build Rust.
2. Revisar o diff e commitar apenas código/documentação intencional, preservando arquivos locais não rastreados.
3. Realizar validações visuais do tray/toast e reinicialização quando a sessão interativa permitir.
4. Continuar triagem de xfails da Fase 26 e testes reais do Telegram da Fase 28.
