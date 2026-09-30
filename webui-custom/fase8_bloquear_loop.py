# ============================================================
# FASE 8 - Bloquear loop de request_confirmation
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# Modificar request_confirmation para bloquear loop
# ============================================================

marcador_antigo = '''@app.post("/request_confirmation")
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
    return {"status": "aguardando", "result": msg}'''

novo_codigo = '''@app.post("/request_confirmation")
def request_confirmation(data: Confirmation):
    global pending_confirmation
    print(f"[REQUEST_CONFIRMATION] acao={data.acao!r} detalhes={data.detalhes!r}")

    # BLOQUEIO ANTI-LOOP: se ja existe uma pendencia recente, NAO cria outra
    if pending_confirmation is not None:
        idade = time.time() - pending_confirmation["timestamp"]
        if idade < CONFIRMATION_TIMEOUT:
            # Pendencia ainda valida - NAO cria nova
            acao_pendente = pending_confirmation["acao"]
            detalhes_pendentes = pending_confirmation.get("detalhes", "")
            msg = (
                f"JA EXISTE UMA CONFIRMACAO PENDENTE: {acao_pendente} ({detalhes_pendentes}). "
                f"NAO chame request_confirmation de novo! "
                f"Se o usuario ja respondeu 'sim', chame a ferramenta destrutiva DIRETAMENTE agora "
                f"(email_delete, delete_file, move_file, email_reply ou email_send)."
            )
            print(f"[REQUEST_CONFIRMATION] BLOQUEADO (loop detectado)")
            return {"status": "bloqueado", "result": msg}
        else:
            # Pendencia expirou - limpa e cria nova
            pending_confirmation = None

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
    msg += " Quando o usuario responder 'sim', chame a ferramenta destrutiva DIRETAMENTE."
    return {"status": "aguardando", "result": msg}'''

if marcador_antigo in conteudo:
    conteudo = conteudo.replace(marcador_antigo, novo_codigo, 1)
    print("[OK] request_confirmation modificado (bloqueio anti-loop)")
else:
    print("[ERRO] Marcador de request_confirmation nao encontrado")
    exit(1)

# ============================================================
# Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] agent.py atualizado com bloqueio anti-loop")
print("[PRONTO] Agora o LLM nao pode chamar request_confirmation duas vezes seguidas.")