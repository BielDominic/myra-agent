# ============================================================
# Adicionar email_delete_by_search (v3 - no final do arquivo)
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# Verificar se ja existe
if "def email_delete_by_search" in conteudo:
    print("[OK] Rota /email_delete_by_search ja existe")
else:
    print("[INFO] Adicionando rota no final do arquivo...")

    conteudo = conteudo.rstrip() + '''


# ============================================================
# FASE 18 - Apagar emails por busca
# ============================================================

@app.post("/email_delete_by_search")
def email_delete_by_search(data: EmailDeleteBySearch):
    print(f"[EMAIL_DELETE_BY_SEARCH] termo={data.termo!r} pasta={data.pasta} limite={data.limite}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, f'(OR SUBJECT "{data.termo}" BODY "{data.termo}")')

        if status != "OK" or not mensagens[0]:
            mail.logout()
            return {"status": "ok", "result": f"Nenhum email encontrado com {data.termo!r}"}

        ids = mensagens[0].split()
        ids_recentes = ids[-data.limite:][::-1]
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

    print("[OK] Rota adicionada no final do arquivo")

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n[PRONTO] agent.py atualizado")