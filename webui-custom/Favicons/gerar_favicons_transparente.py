from PIL import Image
import os
import shutil

origem = r"C:\computer-agent\webui-custom\Favicons\MYRALOGO.jpeg"
pasta_destino = r"C:\computer-agent\webui-custom\Favicons"

if not os.path.exists(origem):
    print(f"[ERRO] Arquivo nao encontrado: {origem}")
    exit(1)

# Abre a imagem e converte para RGBA (com canal alpha)
img = Image.open(origem).convert("RGBA")
print(f"[OK] Imagem carregada: {img.size[0]}x{img.size[1]} pixels")

# Pega os dados dos pixels
data = img.getdata()
novo_data = []

# Torna o preto transparente
# Um pixel eh considerado "preto" se R, G e B forem todos menores que 30
LIMITE = 30
for item in data:
    r, g, b, a = item
    if r < LIMITE and g < LIMITE and b < LIMITE:
        # Torna transparente
        novo_data.append((0, 0, 0, 0))
    else:
        # Mantem o pixel original
        novo_data.append((r, g, b, a))

img.putdata(novo_data)
print(f"[OK] Fundo preto removido (limite: {LIMITE})")

# Salva a versao transparente
caminho_transparente = os.path.join(pasta_destino, "MYRALOGO_transparente.png")
img.save(caminho_transparente, "PNG")
print(f"[OK] Versao transparente salva: MYRALOGO_transparente.png")

# Gera os tamanhos necessarios
tamanhos = {
    "favicon.png": (512, 512),
    "favicon-96x96.png": (96, 96),
    "apple-touch-icon.png": (180, 180),
    "favicon-32x32.png": (32, 32),
    "favicon-16x16.png": (16, 16),
    "logo.png": (512, 512),
}

for nome, tamanho in tamanhos.items():
    img_redim = img.resize(tamanho, Image.LANCZOS)
    caminho = os.path.join(pasta_destino, nome)
    img_redim.save(caminho, "PNG")
    print(f"[OK] {nome} ({tamanho[0]}x{tamanho[1]})")

# Gera o .ico (multi-resolucao)
img_redim = img.resize((256, 256), Image.LANCZOS)
img_redim.save(
    os.path.join(pasta_destino, "favicon.ico"),
    "ICO",
    sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
)
print("[OK] favicon.ico (multi-resolucao)")

# Gera o .svg (placeholder - copia o PNG)
shutil.copy(
    os.path.join(pasta_destino, "favicon.png"),
    os.path.join(pasta_destino, "favicon.svg")
)
print("[OK] favicon.svg (placeholder)")

print("\nTodos os favicons transparentes foram gerados em:", pasta_destino)