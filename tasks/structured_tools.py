"""
FASE 24.2 — Ferramentas estruturadas.
Devolvem dados em formato JSON pro loop adaptativo poder navegar.
"""
import json
import urllib.parse
import re as _re
import requests

AGENT_URL = "http://127.0.0.1:8000"


def _post(rota: str, payload: dict, timeout: int = 60) -> dict:
    """Chama uma rota do agent.py."""
    try:
        r = requests.post(f"{AGENT_URL}{rota}", json=payload, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def _limpar_url_google(url: str) -> str:
    """Remove redirects do Google (/url?q=...) e devolve a URL real."""
    if "/url?" in url and "q=" in url:
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs:
                return qs["q"][0]
        except Exception:
            pass
    return url


def search_google_structured(query: str = "", max_resultados: int = 5) -> dict:
    """Busca no Google e devolve LISTA de resultados estruturados."""
    if not query:
        return {"status": "erro", "result": "Parametro 'query' obrigatorio. Passe query='termo de busca'."}

    try:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(query) + f"&num={max_resultados}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=30)
        html = r.text

        resultados = []
        padrao = _re.compile(r'<a[^>]+href="(/url\?[^\"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3>', _re.DOTALL)
        for match in padrao.finditer(html):
            if len(resultados) >= max_resultados:
                break
            # Deixa parse_qs decodificar o parametro q inteiro; unquote antes
            # faria os & internos da URL de destino virarem separadores da query.
            url_bruta = match.group(1)
            url_real = _limpar_url_google("https://www.google.com" + url_bruta)
            titulo = _re.sub(r"<[^>]+>", "", match.group(2)).strip()
            titulo = titulo.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
            if not url_real.startswith(("http://", "https://")):
                continue
            if url_real.startswith("https://www.google.com/url?"):
                continue
            resultados.append({"titulo": titulo, "url": url_real, "snippet": ""})

        if not resultados:
            return {"status": "erro", "result": "Google nao retornou resultados parseaveis (possivel bloqueio)."}

        return {
            "status": "ok",
            "result": json.dumps({"results": resultados, "count": len(resultados)}, ensure_ascii=False),
            "results": resultados,
            "count": len(resultados),
        }
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def web_search_structured(query: str = "", max_resultados: int = 5) -> dict:
    """Busca via DuckDuckGo e devolve LISTA estruturada."""
    if not query:
        return {"status": "erro", "result": "Parametro 'query' obrigatorio. Passe query='termo de busca'."}

    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(url, data={"q": query}, headers=headers, timeout=30)
        html = r.text

        resultados = []
        padrao = _re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            _re.DOTALL,
        )
        for match in padrao.finditer(html):
            if len(resultados) >= max_resultados:
                break
            link = match.group(1)
            titulo = _re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = _re.sub(r"<[^>]+>", "", match.group(3)).strip()
            titulo = titulo.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
            snippet = snippet.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')

            if "uddg=" in link:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                if "uddg" in parsed:
                    link = parsed["uddg"][0]

            resultados.append({"titulo": titulo, "url": link, "snippet": snippet[:300]})

        if not resultados:
            return {"status": "erro", "result": "DuckDuckGo nao retornou resultados parseaveis."}

        return {
            "status": "ok",
            "result": json.dumps({"results": resultados, "count": len(resultados)}, ensure_ascii=False),
            "results": resultados,
            "count": len(resultados),
        }
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def youtube_search(query: str = "", max_resultados: int = 5) -> dict:
    """Busca videos no YouTube usando yt-dlp."""
    if not query:
        return {"status": "erro", "result": "Parametro 'query' obrigatorio. Passe query='termo de busca'."}
    if not isinstance(max_resultados, int) or isinstance(max_resultados, bool) or max_resultados < 1:
        return {"status": "erro", "result": "max_resultados deve ser um inteiro maior que zero."}

    try:
        import yt_dlp
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_resultados}:{query}", download=False)

        entries = info.get("entries", []) or []
        entries = entries[:max_resultados]
        resultados = []
        for e in entries:
            if not e:
                continue
            vid = e.get("id", "")
            resultados.append({
                "titulo": e.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid}" if vid else e.get("url", ""),
                "id": vid,
                "canal": e.get("uploader") or e.get("channel", ""),
                "duracao": e.get("duration"),
            })

        if not resultados:
            return {"status": "erro", "result": "Nenhum video encontrado no YouTube."}

        return {
            "status": "ok",
            "result": json.dumps({"results": resultados, "count": len(resultados)}, ensure_ascii=False),
            "results": resultados,
            "count": len(resultados),
        }
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def youtube_channel_latest(channel: str = "", max_resultados: int = 3) -> dict:
    """Pega os ultimos videos de um canal do YouTube."""
    if not channel:
        return {"status": "erro", "result": "Parametro 'channel' obrigatorio. Passe channel='@handle' ou channel='nome do canal'."}
    if not isinstance(max_resultados, int) or isinstance(max_resultados, bool) or max_resultados < 1:
        return {"status": "erro", "result": "max_resultados deve ser um inteiro maior que zero."}

    try:
        import yt_dlp
        canal_limpo = channel.strip()

        if canal_limpo.startswith("http"):
            target = canal_limpo
        else:
            handle_base = canal_limpo.lstrip("@").replace(" ", "").lower()
            target = f"https://www.youtube.com/@{handle_base}/videos"

        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlistend": max_resultados,
        }

        # Tentativa 1: como handle direto
        info = None
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target, download=False)
        except Exception as e1:
            # Tentativa 2: busca por nome do canal
            try:
                search_opts = dict(opts)
                search_opts["extract_flat"] = True
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    search_info = ydl.extract_info(f"ytsearch5:{channel}", download=False)

                entries = search_info.get("entries", []) or []
                canal_url = None
                for e in entries:
                    if not e:
                        continue
                    uploader_url = e.get("uploader_url") or ""
                    canal_nome = (e.get("uploader") or e.get("channel") or "").lower()
                    palavras = [p.lower() for p in channel.replace("@", "").split() if len(p) > 2]
                    if canal_nome and palavras and any(p in canal_nome for p in palavras):
                        canal_url = uploader_url
                        if canal_url:
                            break

                if canal_url:
                    target = canal_url
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(target, download=False)
                else:
                    raise e1
            except Exception as e2:
                return {
                    "status": "erro",
                    "result": (
                        f"Nao consegui acessar o canal '{channel}'. "
                        f"Tentativas: handle direto ({type(e1).__name__}), "
                        f"busca por nome ({type(e2).__name__}). "
                        f"Dica: use channel='@handle-oficial' (ex: '@postmalone')."
                    ),
                }

        if not info:
            return {"status": "erro", "result": f"Canal '{channel}' retornou vazio."}

        entries = info.get("entries", [])[:max_resultados] if info.get("entries") else []
        resultados = []
        for e in entries:
            if not e:
                continue
            vid = e.get("id", "")
            resultados.append({
                "titulo": e.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid}" if vid else e.get("url", ""),
                "id": vid,
                "canal": info.get("uploader") or info.get("title", ""),
                "duracao": e.get("duration"),
            })

        if not resultados:
            return {
                "status": "erro",
                "result": f"Canal '{channel}' encontrado mas sem videos acessiveis.",
            }

        return {
            "status": "ok",
            "result": json.dumps({"results": resultados, "count": len(resultados)}, ensure_ascii=False),
            "results": resultados,
            "count": len(resultados),
        }
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def get_current_url() -> dict:
    """Devolve a URL atual do navegador controlado."""
    try:
        result = _post("/get_current_url", {}, timeout=10)
        if result.get("status") == "erro":
            return result
        return {"status": "ok", "result": result.get("url", ""), "url": result.get("url", "")}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def read_page_structured() -> dict:
    """Le a pagina atual e devolve tudo estruturado."""
    try:
        result = _post("/read_page_structured", {}, timeout=15)
        if result.get("status") == "erro":
            return result
        return {
            "status": "ok",
            "result": json.dumps(result, ensure_ascii=False),
            **result,
        }
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def registrar_todas(registrar_ferramenta):
    """Registra todas as ferramentas estruturadas no simple_task."""
    registrar_ferramenta(
        "search_google_structured", search_google_structured,
        "busca no Google e devolve LISTA de links. OBG: passe query='termo de busca'"
    )
    registrar_ferramenta(
        "web_search_structured", web_search_structured,
        "busca na web (DuckDuckGo) e devolve LISTA de links. OBG: passe query='termo de busca'"
    )
    registrar_ferramenta(
        "youtube_search", youtube_search,
        "busca videos no YouTube e devolve LISTA. OBG: passe query='termo de busca'. Ex: query='Post Malone'"
    )
    registrar_ferramenta(
        "youtube_channel_latest", youtube_channel_latest,
        "pega os ultimos videos de um canal do YouTube. OBG: passe channel='@handle-oficial' (ex: '@postmalone', '@MrBeast'), SEM espacos, SEM maiusculas. Se nao souber o handle, use o nome simples."
    )
    registrar_ferramenta(
        "get_current_url", get_current_url,
        "devolve a URL atual do navegador. Sem argumentos."
    )
    registrar_ferramenta(
        "read_page_structured", read_page_structured,
        "le a pagina atual e devolve texto, links, botoes e inputs em JSON. Sem argumentos."
    )