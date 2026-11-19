# MYRA para macOS

## Estado do pacote

A versão macOS é um primeiro pacote nativo da interface Tauri (DMG), com builds separados para Apple Silicon (arm64) e Intel (x64). O backend de automação ainda está em portabilidade: partes de controle de janelas, automação do desktop, captura e inicialização do agente usam APIs específicas do Windows. Portanto, não trate este DMG como paridade funcional completa com o Windows.

## Instalação

1. Baixe o DMG correspondente ao processador do Mac em GitHub Releases.
2. Abra o DMG e arraste MYRA para Applications.
3. Na primeira abertura, macOS pode exigir confirmação em Privacy & Security porque os builds ainda não são assinados/notarizados pela Apple.
4. A interface nativa pode ser explorada; os recursos que dependem do backend Windows permanecem indisponíveis até a conclusão da portabilidade.

## Privacidade e perfil

O objetivo da instalação final é manter dados em `~/Library/Application Support/MYRA`, com workspace, projetos, memória, downloads, perfil de navegador e configuração de modelo separados por conta macOS. O bootstrap completo do backend macOS ainda está pendente.

## Limitações conhecidas

- Controle de janelas e UI Automation do Windows ainda não foi portado.
- Integração do backend, Chromium e Ollama ainda precisa de bootstrap nativo macOS.
- Assinatura Developer ID, notarização e atualização automática ainda não estão configuradas.
