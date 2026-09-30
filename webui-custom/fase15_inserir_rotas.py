import re

caminho = r"C:\computer-agent\agent.py"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# ============================================================
# 1. Novos modelos Pydantic (inserir depois de "class SeeImage")
# ============================================================

marcador_modelos = '''class SeeImage(BaseModel):
    pergunta: str = "Descreva em portugues o que voce ve nesta imagem, em 2 frases."'''

novos_modelos = marcador_modelos + '''


class DeleteFile(BaseModel):
    caminho: str


class CreateDir(BaseModel):
    caminho: str


class MoveFile(BaseModel):
    origem: str
    destino: str


class SearchInFiles(BaseModel):
    termo: str
    extensao: str = ".txt"'''

if marcador_modelos in conteudo:
    conteudo = conteudo.replace(marcador_modelos, novos_modelos, 1)
    print("[OK] 4 novos modelos Pydantic inseridos")
else:
    print("[ERRO] Marcador de modelos nao encontrado")
    exit(1)

# ============================================================
# 2. Novas rotas (inserir no final do arquivo)
# ============================================================

novas_rotas = '''

# ============================================================
# FASE 15 - Ferramentas de arquivo avancadas
# ============================================================

@app.post("/delete_file")
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
        return {"status": "ok", "result": f"Arquivo apagado: {data.caminho}"}
    except Exception as e:
        print(f"[DELETE_FILE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/create_dir")
def create_dir(data: CreateDir):
    print(f"[CREATE_DIR] caminho={data.caminho}")
    try:
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)
        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        os.makedirs(caminho_completo, exist_ok=True)
        return {"status": "ok", "result": f"Pasta criada: {data.caminho}"}
    except Exception as e:
        print(f"[CREATE_DIR] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/move_file")
def move_file(data: MoveFile):
    print(f"[MOVE_FILE] origem={data.origem} destino={data.destino}")
    try:
        origem_completa = os.path.join(WORKSPACE_DIR, data.origem)
        destino_completo = os.path.join(WORKSPACE_DIR, data.destino)

        if not os.path.abspath(origem_completa).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado (origem): fora do workspace"}
        if not os.path.abspath(destino_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado (destino): fora do workspace"}

        if not os.path.exists(origem_completa):
            return {"status": "erro", "result": f"Origem nao encontrada: {data.origem}"}

        os.makedirs(os.path.dirname(destino_completo), exist_ok=True)
        os.replace(origem_completa, destino_completo)
        return {"status": "ok", "result": f"Arquivo movido: {data.origem} -> {data.destino}"}
    except Exception as e:
        print(f"[MOVE_FILE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/search_in_files")
def search_in_files(data: SearchInFiles):
    print(f"[SEARCH_IN_FILES] termo={data.termo!r} extensao={data.extensao!r}")
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        termo_lower = data.termo.lower()
        resultados = []

        for raiz, dirs, arquivos in os.walk(WORKSPACE_DIR):
            for nome in arquivos:
                if data.extensao and not nome.endswith(data.extensao):
                    continue
                caminho_arquivo = os.path.join(raiz, nome)
                try:
                    with open(caminho_arquivo, "r", encoding="utf-8-sig", errors="ignore") as f:
                        for num_linha, linha in enumerate(f, 1):
                            if termo_lower in linha.lower():
                                relativo = os.path.relpath(caminho_arquivo, WORKSPACE_DIR)
                                resultados.append(f"{relativo}:{num_linha}: {linha.strip()[:120]}")
                                if len(resultados) >= 50:
                                    break
                except Exception:
                    pass
                if len(resultados) >= 50:
                    break
            if len(resultados) >= 50:
                break

        if not resultados:
            return {"status": "ok", "result": f"Nenhuma ocorrencia de {data.termo!r} encontrada."}

        return {"status": "ok", "result": f"{len(resultados)} ocorrencia(s):\\n" + "\\n".join(resultados)}
    except Exception as e:
        print(f"[SEARCH_IN_FILES] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}
'''

conteudo = conteudo.rstrip() + novas_rotas

with open(caminho, "w", encoding="utf-8") as f:
    f.write(conteudo)

print("[OK] 4 novas rotas inseridas")
print("[OK] agent.py atualizado com sucesso")