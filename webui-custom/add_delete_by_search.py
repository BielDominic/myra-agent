# ============================================================
# Adicionar email_delete_by_search
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# 1. Adicionar modelo Pydantic (depois de EmailSearch)
marcador_modelo = '''class EmailSearch(BaseModel):
    termo: str
    pasta: str = "INBOX"
    quantidade: int = 10'''

novo_modelo = marcador_modelo + '''


class EmailDeleteBySearch(BaseModel):
    termo: str
    pasta: str = "INBOX"
    limite: int = 50'''

if marcador_modelo in conteudo:
    conteudo = conteudo.replace(marcador_modelo, novo_modelo, 1)
    print("[OK] Modelo EmailDeleteBySearch adicionado")
else:
    print("[AVISO] Marcador de EmailSearch nao encontrado")

# 2. Adicionar rota (depois de email_reply)
marcador_rota = '''        pending_confirmation = None
        return {"status": "ok", "result": f"Resposta enviada para {de_original}"}
    except Exception as e:
        print(f"[EMAIL_REPLY] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}'''

nova_rota = marcador_rota + '''


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
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}'''

if marcador_rota in conteudo:
    conteudo = conteudo.replace(marcador_rota, nova_rota, 1)
    print("[OK] Rota /email_delete_by_search adicionada")
else:
    print("[AVISO] Marcador de email_reply nao encontrado")

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py atualizado com email_delete_by_search")
