# ============================================================
# FASE 8 v3 - confirm_and_execute
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Modificar classe Confirmation (adicionar acao_pendente e parametros)
# ============================================================

if "class Confirmation(BaseModel):" not in conteudo:
    print("[ERRO] Classe Confirmation nao encontrada")
    exit(1)

import re
padrao_confirmation = r'class Confirmation\(BaseModel\):\s*\n(\s+\w+:.*\n?)+'
match = re.search(padrao_confirmation, conteudo)

if not match:
    print("[ERRO] Nao consegui encontrar a definicao da classe Confirmation")
    exit(1)

classe_antiga = match.group(0)

classe_nova = '''class Confirmation(BaseModel):
    acao: str
    detalhes: str = ""
    acao_pendente: str = ""
    parametros: dict = {}'''

conteudo = conteudo.replace(classe_antiga, classe_nova, 1)
print("[OK] Classe Confirmation modificada")

# ============================================================
# 2. Modificar request_confirmation para guardar acao_pendente e parametros
# ============================================================

marcador_rc = '''    pending_confirmation = {
        "acao": data.acao,
        "detalhes": data.detalhes,
        "timestamp": time.time(),
        "confirmada": False,
    }'''

novo_rc = '''    pending_confirmation = {
        "acao": data.acao,
        "detalhes": data.detalhes,
        "timestamp": time.time(),
        "confirmada": False,
        "acao_pendente": data.acao_pendente,
        "parametros": data.parametros,
    }'''

if marcador_rc in conteudo:
    conteudo = conteudo.replace(marcador_rc, novo_rc, 1)
    print("[OK] request_confirmation modificado")
else:
    print("[AVISO] Marcador de pending_confirmation nao encontrado")

# ============================================================
# 3. Adicionar rota confirm_and_execute (depois de cancel_confirmation)
# ============================================================

marcador_cancel = '''@app.post("/cancel_confirmation")
def cancel_confirmation():
    global pending_confirmation
    print("[CANCEL_CONFIRMATION]")
    if pending_confirmation is None:
        return {"status": "ok", "result": "Nenhuma acao pendente para cancelar."}
    pending_confirmation = None
    return {"status": "ok", "result": "Confirmacao cancelada."}'''

nova_rota = marcador_cancel + '''


@app.post("/confirm_and_execute")
def confirm_and_execute():
    """Executa a acao que estava pendente de confirmacao."""
    global pending_confirmation
    print("[CONFIRM_AND_EXECUTE]")

    if pending_confirmation is None:
        return {"status": "erro", "result": "Nenhuma acao pendente de confirmacao."}

    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    acao = pending_confirmation.get("acao_pendente", "")
    params = pending_confirmation.get("parametros", {})

    if not acao:
        return {"status": "erro", "result": "Nenhuma acao pendente configurada. Use request_confirmation com acao_pendente e parametros."}

    print(f"[CONFIRM_AND_EXECUTE] Executando {acao} com {params}")

    try:
        if acao == "email_delete":
            resultado = email_delete(EmailDelete(**params))
        elif acao == "delete_file":
            resultado = delete_file(DeleteFile(**params))
        elif acao == "move_file":
            resultado = move_file(MoveFile(**params))
        elif acao == "email_reply":
            resultado = email_reply(EmailReply(**params))
        elif acao == "email_send":
            resultado = email_send(EmailSend(**params))
        else:
            return {"status": "erro", "result": f"Acao desconhecida: {acao}"}

        pending_confirmation = None
        return resultado
    except Exception as e:
        print(f"[CONFIRM_AND_EXECUTE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro ao executar {acao}: {type(e).__name__}: {e}"}'''

if marcador_cancel in conteudo:
    conteudo = conteudo.replace(marcador_cancel, nova_rota, 1)
    print("[OK] Rota confirm_and_execute adicionada")
else:
    print("[ERRO] Marcador de cancel_confirmation nao encontrado")
    exit(1)

# ============================================================
# 4. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py atualizado com confirm_and_execute")
print("[PRONTO] Agora o LLM so precisa chamar confirm_and_execute() apos o 'sim'")
