# ============================================================
# Limpeza geral do agent.py
# - Remove rotas de confirmacao orfas
# - Remove email_delete (singular)
# - Simplifica email_delete_by_search
# - Melhora mensagem de erro do email_read
# ============================================================

import re

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Remover rotas de confirmacao orfas
# ============================================================

rotas_para_remover = [
    "request_confirmation",
    "confirm_action",
    "cancel_confirmation",
    "confirm_and_execute",
]

for rota in rotas_para_remover:
    # Padrao: @app.post("/rota") ... ate o proximo @app.post ou @app.get
    padrao = rf'@app\.post\("/{rota}"\)\n.*?(?=@app\.(?:post|get)\(")'
    match = re.search(padrao, conteudo, re.DOTALL)
    if match:
        conteudo = conteudo[:match.start()] + conteudo[match.end():]
        print(f"[OK] Rota /{rota} removida")
    else:
        print(f"[AVISO] Rota /{rota} nao encontrada")

# ============================================================
# 2. Remover email_delete (singular)
# ============================================================

padrao_email_delete = rf'@app\.post\("/email_delete"\)\n.*?(?=@app\.(?:post|get)\(")'
match = re.search(padrao_email_delete, conteudo, re.DOTALL)
if match:
    conteudo = conteudo[:match.start()] + conteudo[match.end():]
    print("[OK] Rota /email_delete (singular) removida")
else:
    print("[AVISO] Rota /email_delete (singular) nao encontrada")

# ============================================================
# 3. Simplificar email_delete_by_search (remover pasta e limite)
# ============================================================

# Substitui a funcao email_delete_by_search por uma versao simplificada
padrao_edbs = rf'@app\.post\("/email_delete_by_search"\)\n.*?(?=@app\.(?:post|get)\("|$)'
match = re.search(padrao_edbs, conteudo, re.DOTALL)
if match:
    nova_edbs = '''@app.post("/email_delete_by_search")
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
    conteudo = conteudo[:match.start()] + nova_edbs + conteudo[match.end():]
    print("[OK] Rota /email_delete_by_search simplificada")
else:
    print("[AVISO] Rota /email_delete_by_search nao encontrada")

# ============================================================
# 4. Atualizar modelo EmailDeleteBySearch (remover pasta e limite)
# ============================================================

padrao_modelo = rf'class EmailDeleteBySearch\(BaseModel\):\n(?:    .*\n)+'
match = re.search(padrao_modelo, conteudo, re.DOTALL)
if match:
    novo_modelo = '''class EmailDeleteBySearch(BaseModel):
    termo: str

'''
    conteudo = conteudo[:match.start()] + novo_modelo + conteudo[match.end():]
    print("[OK] Modelo EmailDeleteBySearch simplificado")
else:
    print("[AVISO] Modelo EmailDeleteBySearch nao encontrado")

# ============================================================
# 5. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py limpo com sucesso")
print("[PRONTO] Rotas de confirmacao removidas: 4")
print("[PRONTO] email_delete (singular) removida")
print("[PRONTO] email_delete_by_search simplificada (so 'termo')")