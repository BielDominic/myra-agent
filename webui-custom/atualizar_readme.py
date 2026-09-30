import re

caminho = r"C:\computer-agent\README.md"

with open(caminho, "r", encoding="utf-8") as f:
    conteudo = f.read()

# Marcador: onde inserir (depois do aviso sobre o volume open-webui)
marcador = 'ATENCAO: o volume "open-webui" guarda todos os dados (conversas, usuarios, configuracoes). Nunca remova esse volume.'

# Nova secao de favicons
nova_secao = '''

### Favicons e logo customizados

O MYRA usa favicons e logo proprios (o olho roxo/azul). Para isso, usamos:

1. Uma pasta no host com as imagens: C:\\computer-agent\\webui-custom\\Favicons\\
2. O Nginx serve esses arquivos no lugar dos originais do Open WebUI.

#### Arquivos necessarios

| Arquivo | Tamanho | Funcao |
|---|---|---|
| favicon.png | 512x512 | Favicon principal |
| favicon.ico | multi | Navegadores antigos |
| favicon.svg | 512x512 | Navegadores modernos |
| favicon-96x96.png | 96x96 | Android/Chrome |
| favicon-32x32.png | 32x32 | Navegadores antigos |
| favicon-16x16.png | 16x16 | Aba do navegador |
| apple-touch-icon.png | 180x180 | iOS/Safari |
| logo.png | 512x512 | Logo da sidebar |
| MYRALOGO.jpeg | original | Imagem original |

#### Como gerar os favicons

Se voce trocar a imagem original (MYRALOGO.jpeg), rode:

    cd C:\\computer-agent
    .\\venv\\Scripts\\Activate.ps1
    python C:\\computer-agent\\webui-custom\\Favicons\\gerar_favicons_transparente.py
    docker restart myra-proxy

O script:
1. Abre o MYRALOGO.jpeg
2. Remove o fundo preto (torna transparente)
3. Gera os 8 arquivos de favicon
4. Salva tudo em Favicons\\

#### Como recriar o myra-proxy com os favicons

    docker rm -f myra-proxy
    docker run -d --name myra-proxy -p 8082:80 -v C:\\computer-agent\\webui-custom\\nginx.conf:/etc/nginx/conf.d/default.conf -v C:\\computer-agent\\webui-custom\\Favicons:/usr/share/nginx/html --link open-webui-custom:open-webui-custom nginx:alpine

ATENCAO: a flag -v extra monta a pasta Favicons em /usr/share/nginx/html dentro do container. Sem ela, o Nginx nao encontra os favicons customizados.

#### Ajuste do limite de transparencia

O script usa limite = 30 para remover o preto. Se sobrarem bordas escuras, aumente para 40 ou 50. Se apagar partes do logo, diminua para 20.

Edite a linha no gerar_favicons_transparente.py:

    limite = 30   # ajuste aqui

E rode de novo.

'''

# Insere a nova secao depois do marcador
if marcador in conteudo:
    conteudo = conteudo.replace(marcador, marcador + nova_secao)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    print("[OK] Secao de favicons adicionada ao README")
else:
    print("[ERRO] Marcador nao encontrado no README")