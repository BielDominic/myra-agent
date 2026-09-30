# ============================================================
# FASE 18 - Detectar nome da pasta Trash automaticamente
# ============================================================

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Adicionar funcao _get_trash_folder() depois de _conectar_imap
# ============================================================

marcador_imap = '''def _conectar_imap():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise Exception("GMAIL_USER ou GMAIL_APP_PASSWORD nao configurados")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return mail'''

nova_funcao = marcador_imap + '''


def _get_trash_folder(mail):
    """Detecta o nome da pasta Lixeira do Gmail (Trash, Lixeira, Papelera, etc)."""
    try:
        status, pastas = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"

        for pasta in pastas:
            nome = pasta.decode("utf-8", errors="ignore")
            # Procura por \\Trash (flag oficial do IMAP)
            if "\\\\Trash" in nome:
                # Extrai o nome entre as ultimas aspas
                partes = nome.split('"')
                if len(partes) >= 2:
                    return partes[-2]
        return "[Gmail]/Trash"
    except Exception:
        return "[Gmail]/Trash"'''

if marcador_imap in conteudo:
    conteudo = conteudo.replace(marcador_imap, nova_funcao, 1)
    print("[OK] Funcao _get_trash_folder adicionada")
else:
    print("[AVISO] Marcador de _conectar_imap nao encontrado")

# ============================================================
# 2. Substituir todas as ocorrencias de "[Gmail]/Lixeira" por "_trash"
# ============================================================

# Substitui a string literal "[Gmail]/Lixeira" por uma variavel local
ocorrencias = conteudo.count('"[Gmail]/Lixeira"')
print(f"[INFO] Ocorrencias de '[Gmail]/Lixeira': {ocorrencias}")

# Em cada rota que usa "[Gmail]/Lixeira", precisamos:
# a) Adicionar a linha "trash = _get_trash_folder(mail)" apos "mail = _conectar_imap()"
# b) Substituir "[Gmail]/Lixeira" por trash

# Vamos fazer isso por rota:
rotas_com_lixeira = ["email_move", "email_delete"]

for rota in rotas_com_lixeira:
    # Procura a definicao da rota
    marcador_rota = f'def {rota}(data:'
    if marcador_rota not in conteudo:
        print(f"[AVISO] Rota {rota} nao encontrada")
        continue

    # Encontra o trecho da rota
    idx_inicio = conteudo.find(marcador_rota)
    idx_fim = conteudo.find("@app.post", idx_inicio + 1)
    if idx_fim == -1:
        idx_fim = len(conteudo)

    trecho = conteudo[idx_inicio:idx_fim]

    # Substitui "mail = _conectar_imap()" por "mail = _conectar_imap()\n        trash = _get_trash_folder(mail)"
    if "mail = _conectar_imap()" in trecho and "trash = _get_trash_folder" not in trecho:
        trecho = trecho.replace(
            "mail = _conectar_imap()",
            "mail = _conectar_imap()\n        trash = _get_trash_folder(mail)",
            1
        )

    # Substitui "[Gmail]/Lixeira" por trash
    trecho = trecho.replace('"[Gmail]/Lixeira"', "trash")

    # Atualiza o conteudo
    conteudo = conteudo[:idx_inicio] + trecho + conteudo[idx_fim:]
    print(f"[OK] Rota {rota} ajustada")

# ============================================================
# 3. Substituir o valor padrao do modelo EmailMove
# ============================================================

conteudo = conteudo.replace(
    'pasta_destino: str = "[Gmail]/Lixeira"',
    'pasta_destino: str = "[Gmail]/Trash"'
)
conteudo = conteudo.replace(
    'pasta_destino: str = "[Gmail]/Lixeira"',
    'pasta_destino: str = "[Gmail]/Trash"'
)

# Substitui tambem o texto de mensagem que menciona "Lixeira"
conteudo = conteudo.replace(
    'movido para a Lixeira',
    'movido para a Lixeira (Trash)'
)

# ============================================================
# 4. Salvar
# ============================================================

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\\n[PRONTO] agent.py atualizado com deteccao automatica de Trash")
print("[PRONTO] Agora o agent.py detecta o nome da Lixeira (Trash, Lixeira, etc)")
