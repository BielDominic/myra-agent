# ============================================================
# Re-adicionar _get_trash_folder + email_delete_by_search
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# 1. Re-adicionar _get_trash_folder (depois de _conectar_imap)
if "_get_trash_folder" not in conteudo:
    print("[INFO] Adicionando _get_trash_folder...")
    marcador_imap = '''def _conectar_imap():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise Exception("GMAIL_USER ou GMAIL_APP_PASSWORD nao configurados")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return mail'''

    if marcador_imap in conteudo:
        nova_funcao = marcador_imap + '''


def _get_trash_folder(mail):
    """Detecta o nome da pasta Lixeira do Gmail (Trash, Lixeira, Papelera, etc)."""
    try:
        status, pastas = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"

        for pasta in pastas:
            nome = pasta.decode("utf-8", errors="ignore")
            if "\\\\Trash" in nome:
                partes = nome.split('"')
                if len(partes) >= 2:
                    return partes[-2]
        return "[Gmail]/Trash"
    except Exception:
        return "[Gmail]/Trash"'''
        conteudo = conteudo.replace(marcador_imap, nova_funcao, 1)
        print("[OK] _get_trash_folder adicionada")
    else:
        print("[ERRO] Marcador _conectar_imap nao encontrado")
        exit(1)
else:
    print("[OK] _get_trash_folder ja existe")

# 2. Verificar se a rota existe
if "def email_delete_by_search" not in conteudo:
    print("[INFO] Adicionando rota /email_delete_by_search...")
    conteudo = conteudo.rstrip() + '''


@app.post("/email_delete_by_search")
def email_delete_by_search(data: EmailDeleteBySearch):
    print(f"[EMAIL_DELETE_BY_SEARCH] termo={data.termo!r}")
    try:
        mail = _conectar_imap()
        mail.select("INBOX")
        status, mensagens = mail.search(None, f'(OR SUBJECT "{data.termo}" BODY "{data.termo}")')

        if status != "OK" or not mensagens[0]:
            mail.logout()
            return {"status": "ok", "result": f"Nenhum email encontrado com {data.termo!r}"}

        ids = mensagens[0].split()
        ids_recentes = ids[-200:][::-1]
        trash = _get_trash_folder(mail)

        apagados = 0
        for eid in ids_recentes:
            try:
                mail.copy(eid, trash)
                mail.store(eid, "+FLAGS", "\\\\Deleted")
                apagados += 1
            except Exception:
                pass

        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"{apagados} email(s) com {data.termo!r} movidos para a Lixeira"}
    except Exception as e:
        print(f"[EMAIL_DELETE_BY_SEARCH] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}
'''
    print("[OK] Rota adicionada")
else:
    print("[OK] Rota ja existe")

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] agent.py atualizado")