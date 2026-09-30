import re

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Adicionar imports necessarios (time)
# ============================================================

if "import time" not in conteudo:
    conteudo = conteudo.replace(
        "import datetime",
        "import datetime\nimport time",
        1
    )
    print("[OK] import time adicionado")

# ============================================================
# 2. Adicionar variaveis globais (pending_confirmation)
# ============================================================

marcador_globais = 'GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")'

novas_globais = marcador_globais + '''

# ============================================================
# CONFIRMACAO PENDENTE (FASE 8)
# ============================================================
pending_confirmation = None  # {"acao": ..., "detalhes": ..., "timestamp": ..., "confirmada": False}
CONFIRMATION_TIMEOUT = 300  # 5 minutos em segundos'''

if marcador_globais in conteudo:
    conteudo = conteudo.replace(marcador_globais, novas_globais, 1)
    print("[OK] Variaveis globais de confirmacao adicionadas")
else:
    print("[ERRO] Marcador de globais nao encontrado")
    exit(1)

# ============================================================
# 3. Modificar request_confirmation
# ============================================================

marcador_rc = '''@app.post("/request_confirmation")
def request_confirmation(data: Confirmation):
    print(f"[REQUEST_CONFIRMATION] acao={data.acao!r} detalhes={data.detalhes!r}")
    msg = f"CONFIRMACAO NECESSARIA: {data.acao}"
    if data.detalhes:
        msg += f" ({data.detalhes})"
    msg += ". Aguardando resposta do usuario (sim/nao). NAO execute a acao ate o usuario confirmar."
    return {"status": "aguardando", "result": msg}'''

novo_rc = '''@app.post("/request_confirmation")
def request_confirmation(data: Confirmation):
    global pending_confirmation
    print(f"[REQUEST_CONFIRMATION] acao={data.acao!r} detalhes={data.detalhes!r}")

    pending_confirmation = {
        "acao": data.acao,
        "detalhes": data.detalhes,
        "timestamp": time.time(),
        "confirmada": False,
    }

    msg = f"CONFIRMACAO NECESSARIA: {data.acao}"
    if data.detalhes:
        msg += f" ({data.detalhes})"
    msg += ". Aguardando resposta do usuario (sim/nao)."
    msg += " Quando o usuario responder 'sim', chame a ferramenta confirm_action() ANTES de executar a acao."
    return {"status": "aguardando", "result": msg}


@app.post("/confirm_action")
def confirm_action():
    global pending_confirmation
    print("[CONFIRM_ACTION]")

    if pending_confirmation is None:
        return {"status": "erro", "result": "Nenhuma acao pendente de confirmacao."}

    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada (mais de 5 minutos). Refaca a solicitacao."}

    pending_confirmation["confirmada"] = True
    acao = pending_confirmation["acao"]
    return {"status": "ok", "result": f"Confirmacao registrada para: {acao}. Agora voce pode executar a acao."}


@app.post("/cancel_confirmation")
def cancel_confirmation():
    global pending_confirmation
    print("[CANCEL_CONFIRMATION]")
    if pending_confirmation is None:
        return {"status": "ok", "result": "Nenhuma acao pendente para cancelar."}
    pending_confirmation = None
    return {"status": "ok", "result": "Confirmacao cancelada."}'''

if marcador_rc in conteudo:
    conteudo = conteudo.replace(marcador_rc, novo_rc, 1)
    print("[OK] request_confirmation modificado + confirm_action e cancel_confirmation adicionados")
else:
    print("[ERRO] Marcador de request_confirmation nao encontrado")
    exit(1)

# ============================================================
# 4. Modificar delete_file (adicionar verificacao)
# ============================================================

marcador_df = '''@app.post("/delete_file")
def delete_file(data: DeleteFile):
    print(f"[DELETE_FILE] caminho={data.caminho}")
    try:
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)
        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        if not os.path.exists(caminho_completo):
            return {"status": "erro", "result": f"Arquivo nao encontrado: {data.caminho}"}

        if not os.path.isfile(caminho_completo):
            return {"status": "erro", "result": f"Nao e um arquivo: {data.caminho}"}

        os.remove(caminho_completo)
        return {"status": "ok", "result": f"Arquivo apagado: {data.caminho}"}'''

novo_df = '''@app.post("/delete_file")
def delete_file(data: DeleteFile):
    global pending_confirmation
    print(f"[DELETE_FILE] caminho={data.caminho}")

    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if not pending_confirmation.get("confirmada"):
        return {"status": "erro", "result": "Confirmacao pendente. O usuario precisa responder 'sim' e voce precisa chamar confirm_action()."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    try:
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)
        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        if not os.path.exists(caminho_completo):
            return {"status": "erro", "result": f"Arquivo nao encontrado: {data.caminho}"}

        if not os.path.isfile(caminho_completo):
            return {"status": "erro", "result": f"Nao e um arquivo: {data.caminho}"}

        os.remove(caminho_completo)
        pending_confirmation = None
        return {"status": "ok", "result": f"Arquivo apagado: {data.caminho}"}'''

if marcador_df in conteudo:
    conteudo = conteudo.replace(marcador_df, novo_df, 1)
    print("[OK] delete_file modificado (com verificacao de confirmacao)")
else:
    print("[AVISO] Marcador de delete_file nao encontrado (pode ja estar modificado)")

# ============================================================
# 5. Modificar move_file
# ============================================================

marcador_mf = '''@app.post("/move_file")
def move_file(data: MoveFile):
    print(f"[MOVE_FILE] origem={data.origem} destino={data.destino}")
    try:'''

novo_mf = '''@app.post("/move_file")
def move_file(data: MoveFile):
    global pending_confirmation
    print(f"[MOVE_FILE] origem={data.origem} destino={data.destino}")

    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if not pending_confirmation.get("confirmada"):
        return {"status": "erro", "result": "Confirmacao pendente. O usuario precisa responder 'sim' e voce precisa chamar confirm_action()."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    try:'''

if marcador_mf in conteudo:
    conteudo = conteudo.replace(marcador_mf, novo_mf, 1)
    # Adiciona limpeza da pendencia antes do return de sucesso
    conteudo = conteudo.replace(
        'return {"status": "ok", "result": f"Arquivo movido: {data.origem} -> {data.destino}"}',
        'pending_confirmation = None\n        return {"status": "ok", "result": f"Arquivo movido: {data.origem} -> {data.destino}"}',
        1
    )
    print("[OK] move_file modificado (com verificacao de confirmacao)")
else:
    print("[AVISO] Marcador de move_file nao encontrado")

# ============================================================
# 6. Modificar email_send
# ============================================================

marcador_es = '''@app.post("/email_send")
def email_send(data: EmailSend):
    print(f"[EMAIL_SEND] para={data.para} assunto={data.assunto}")
    try:'''

novo_es = '''@app.post("/email_send")
def email_send(data: EmailSend):
    global pending_confirmation
    print(f"[EMAIL_SEND] para={data.para} assunto={data.assunto}")

    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if not pending_confirmation.get("confirmada"):
        return {"status": "erro", "result": "Confirmacao pendente. O usuario precisa responder 'sim' e voce precisa chamar confirm_action()."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    try:'''

if marcador_es in conteudo:
    conteudo = conteudo.replace(marcador_es, novo_es, 1)
    print("[OK] email_send modificado (com verificacao de confirmacao)")
else:
    print("[AVISO] Marcador de email_send nao encontrado")

# ============================================================
# 7. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] agent.py atualizado com FASE 8 (confirmacao robusta)")