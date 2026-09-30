import re

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# Remover a verificacao "if not pending_confirmation.get('confirmada')"
# de delete_file, move_file e email_send
# ============================================================

bloco_remover = '''    if not pending_confirmation.get("confirmada"):
        return {"status": "erro", "result": "Confirmacao pendente. O usuario precisa responder 'sim' e voce precisa chamar confirm_action()."}
'''

# Conta quantas vezes o bloco aparece
ocorrencias = conteudo.count(bloco_remover)
print(f"[INFO] Bloco de verificacao 'confirmada' encontrado {ocorrencias} vezes")

if ocorrencias >= 3:
    conteudo = conteudo.replace(bloco_remover, "")
    print(f"[OK] Bloco removido de {ocorrencias} locais (delete_file, move_file, email_send)")
else:
    print(f"[AVISO] Bloco encontrado apenas {ocorrencias} vezes (esperado >= 3)")

# ============================================================
# Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] agent.py simplificado para fluxo de 2 etapas")
print("[PRONTO] Agora: request_confirmation -> delete_file (sem confirm_action)")