# ============================================================
# Remover a verificacao de confirmacao das funcoes destrutivas
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# Bloco de verificacao a ser removido
bloco = '''    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

'''

# Conta ocorrencias
ocorrencias = conteudo.count(bloco)
print(f"[INFO] Bloco de confirmacao encontrado {ocorrencias} vezes")

if ocorrencias >= 3:
    conteudo = conteudo.replace(bloco, "")
    print(f"[OK] Bloco removido de {ocorrencias} locais")
else:
    print(f"[AVISO] Bloco encontrado apenas {ocorrencias} vezes")

# Tambem remove a limpeza da pendencia (pending_confirmation = None) dos returns de sucesso
conteudo = conteudo.replace(
    "        pending_confirmation = None\n        return {\"status\": \"ok\"",
    "        return {\"status\": \"ok\""
)

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py atualizado: confirmacao removida das funcoes destrutivas")
print("[PRONTO] Agora email_delete, email_send, email_reply, delete_file e move_file executam DIRETO")
