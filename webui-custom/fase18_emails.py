# ============================================================
# FASE 18 - Emails avancados
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Adicionar novos modelos Pydantic (depois de "class EmailSend")
# ============================================================

marcador_modelos = '''class EmailSend(BaseModel):
    para: str
    assunto: str
    corpo: str'''

novos_modelos = marcador_modelos + '''


class EmailMark(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"


class EmailMove(BaseModel):
    indice: int = 0
    pasta_origem: str = "INBOX"
    pasta_destino: str = "[Gmail]/Lixeira"


class EmailDelete(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"


class EmailSearch(BaseModel):
    termo: str
    pasta: str = "INBOX"
    quantidade: int = 10


class EmailReply(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"
    corpo: str'''

if marcador_modelos in conteudo:
    conteudo = conteudo.replace(marcador_modelos, novos_modelos, 1)
    print("[OK] 5 novos modelos Pydantic inseridos")
else:
    print("[ERRO] Marcador de EmailSend nao encontrado")
    exit(1)

# ============================================================
# 2. Adicionar novas rotas (depois de "def email_send")
# ============================================================

marcador_rotas = '''        return {"status": "ok", "result": f"Email enviado para {data.para}"}
    except Exception as e:
        print(f"[EMAIL_SEND] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}'''

novas_rotas = marcador_rotas + '''


@app.post("/email_mark_read")
def email_mark_read(data: EmailMark):
    print(f"[EMAIL_MARK_READ] indice={data.indice} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "+FLAGS", "\\\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_READ] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_mark_unread")
def email_mark_unread(data: EmailMark):
    print(f"[EMAIL_MARK_UNREAD] indice={data.indice} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "-FLAGS", "\\\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como NAO lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_UNREAD] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_move")
def email_move(data: EmailMove):
    print(f"[EMAIL_MOVE] indice={data.indice} origem={data.pasta_origem} destino={data.pasta_destino}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta_origem)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, data.pasta_destino)
        mail.store(eid, "+FLAGS", "\\\\Deleted")
        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} movido de {data.pasta_origem} para {data.pasta_destino}"}
    except Exception as e:
        print(f"[EMAIL_MOVE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_delete")
def email_delete(data: EmailDelete):
    global pending_confirmation
    print(f"[EMAIL_DELETE] indice={data.indice} pasta={data.pasta}")

    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, "[Gmail]/Lixeira")
        mail.store(eid, "+FLAGS", "\\\\Deleted")
        mail.expunge()
        mail.logout()
        pending_confirmation = None
        return {"status": "ok", "result": f"Email {data.indice} movido para a Lixeira"}
    except Exception as e:
        print(f"[EMAIL_DELETE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_search")
def email_search(data: EmailSearch):
    print(f"[EMAIL_SEARCH] termo={data.termo!r} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        # Busca por assunto OU corpo
        status, mensagens = mail.search(None, f'(OR SUBJECT "{data.termo}" BODY "{data.termo}")')
        if status != "OK" or not mensagens[0]:
            mail.logout()
            return {"status": "ok", "result": f"Nenhum email encontrado com {data.termo!r}"}

        ids = mensagens[0].split()
        ids_recentes = ids[-data.quantidade:][::-1]

        resultado = []
        for i, eid in enumerate(ids_recentes):
            status, dados = mail.fetch(eid, "(RFC822)")
            msg = email_lib.message_from_bytes(dados[0][1])
            assunto = _decodificar(msg.get("Subject", "(sem assunto)"))
            de = _decodificar(msg.get("From", "(sem remetente)"))
            data_email = msg.get("Date", "(sem data)")
            resultado.append(f"[{i}] De: {de} | Assunto: {assunto} | Data: {data_email}")

        mail.logout()
        if not resultado:
            return {"status": "ok", "result": f"Nenhum email encontrado com {data.termo!r}"}
        return {"status": "ok", "result": "\\n".join(resultado)}
    except Exception as e:
        print(f"[EMAIL_SEARCH] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_reply")
def email_reply(data: EmailReply):
    global pending_confirmation
    print(f"[EMAIL_REPLY] indice={data.indice} pasta={data.pasta}")

    # FASE 8: verificar confirmacao
    if pending_confirmation is None:
        return {"status": "erro", "result": "Aguardando confirmacao. Chame request_confirmation primeiro."}
    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        status, dados = mail.fetch(eid, "(RFC822)")
        msg_original = email_lib.message_from_bytes(dados[0][1])

        assunto_original = _decodificar(msg_original.get("Subject", ""))
        de_original = msg_original.get("From", "")
        message_id_original = msg_original.get("Message-ID", "")

        mail.logout()

        # Envia a resposta via SMTP
        msg = EmailMessage()
        msg["From"] = GMAIL_USER
        msg["To"] = de_original
        msg["Subject"] = f"Re: {assunto_original}"
        if message_id_original:
            msg["In-Reply-To"] = message_id_original
            msg["References"] = message_id_original
        msg.set_content(data.corpo)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        pending_confirmation = None
        return {"status": "ok", "result": f"Resposta enviada para {de_original}"}
    except Exception as e:
        print(f"[EMAIL_REPLY] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}'''

if marcador_rotas in conteudo:
    conteudo = conteudo.replace(marcador_rotas, novas_rotas, 1)
    print("[OK] 6 novas rotas inseridas")
else:
    print("[ERRO] Marcador de email_send nao encontrado")
    exit(1)

# ============================================================
# 3. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py atualizado com FASE 18 (emails avancados)")