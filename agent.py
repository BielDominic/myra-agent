from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import os
import imaplib
import smtplib
import subprocess
import tempfile
import datetime
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import re as _re
import yt_dlp
from tasks.simple_task import executar_task, registrar_ferramenta
from email.message import EmailMessage
from email.header import decode_header
import email as email_lib

app = FastAPI()

browser = None
context = None
page = None
playwright = None

PERFIL_DIR = r"C:\computer-agent\chrome_profile"
NOTES_FILE = r"C:\computer-agent\notes.txt"
WORKSPACE_DIR = r"C:\computer-agent\workspace"
SCREENSHOTS_DIR = r"C:\computer-agent\screenshots"
LLM_EYES_URL = "http://127.0.0.1:8081/v1/chat/completions"

OPENWEBUI_URL = "http://127.0.0.1:8080"
OPENWEBUI_API_KEY = os.environ.get("OPENWEBUI_API_KEY", "")

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

CIDADE_PADRAO = "Tarmonbarry, Ireland"

pending_confirmation = None
CONFIRMATION_TIMEOUT = 300

_chat_cache = {"data": None, "timestamp": 0}
CHAT_CACHE_TTL = 5


class OpenURL(BaseModel):
    url: str


class SearchGoogle(BaseModel):
    query: str


class ClickElement(BaseModel):
    text: str = None
    selector: str = None


class TypeText(BaseModel):
    selector: str = None
    text: str
    field_text: str = None


class PressKey(BaseModel):
    key: str


class Wait(BaseModel):
    seconds: float


class Confirmation(BaseModel):
    acao: str
    detalhes: str = ""
    acao_pendente: str = ""
    parametros: dict = {}


class EmailList(BaseModel):
    quantidade: int = 5
    pasta: str = "INBOX"


class EmailRead(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"


class EmailSend(BaseModel):
    para: str
    assunto: str
    corpo: str


class EmailMark(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"


class EmailMove(BaseModel):
    indice: int = 0
    pasta_origem: str = "INBOX"
    pasta_destino: str = "[Gmail]/Trash"


class EmailDelete(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"


class EmailSearch(BaseModel):
    termo: str
    pasta: str = "INBOX"
    quantidade: int = 10


class EmailDeleteBySearch(BaseModel):
    termo: str
    pasta: str = "INBOX"
    limite: int = 50


class EmailReply(BaseModel):
    indice: int = 0
    pasta: str = "INBOX"
    corpo: str


class SaveNote(BaseModel):
    texto: str


class GetWeather(BaseModel):
    cidade: str = ""


class RunPython(BaseModel):
    codigo: str


class ListDir(BaseModel):
    caminho: str = "."


class ReadFile(BaseModel):
    caminho: str


class WriteFile(BaseModel):
    caminho: str
    conteudo: str


class WebSearch(BaseModel):
    query: str
    max_resultados: int = 5


class SeeImage(BaseModel):
    pergunta: str = "Descreva em portugues o que voce ve nesta imagem, em 2 frases."


class DeleteFile(BaseModel):
    caminho: str


class CreateDir(BaseModel):
    caminho: str


class MoveFile(BaseModel):
    origem: str
    destino: str


class SearchInFiles(BaseModel):
    termo: str
    extensao: str = ".txt"


class PCMoveMouse(BaseModel):
    x: int
    y: int
    duration: float = 0.3


class PCClick(BaseModel):
    x: int = None
    y: int = None
    button: str = "left"


class PCClickXY(BaseModel):
    x: int = None
    y: int = None


class PCTypeText(BaseModel):
    text: str
    interval: float = 0.02


class PCPressKey(BaseModel):
    key: str


class PCHotkey(BaseModel):
    keys: list


class PCScroll(BaseModel):
    amount: int


class PCScreenshot(BaseModel):
    salvar: bool = True


class PCFocusWindow(BaseModel):
    titulo: str


class ChatList(BaseModel):
    quantidade: int = 20


class ChatDelete(BaseModel):
    indice: int = 0
    chat_id: str = None


class ChatDeleteBySearch(BaseModel):
    termo: str
    limite: int = 20


class ChatDeleteAll(BaseModel):
    confirmar: bool = False


class ChatRename(BaseModel):
    indice: int = 0
    chat_id: str = None
    novo_titulo: str


class CodeInput(BaseModel):
    codigo: str
    contexto: str = ""


class CodeGenerate(BaseModel):
    descricao: str
    linguagem: str = "python"


class CodeRefactor(BaseModel):
    codigo: str
    objetivo: str


class CodeConvert(BaseModel):
    codigo: str
    linguagem_origem: str = "python"
    linguagem_destino: str


class CodeRunFile(BaseModel):
    caminho: str
    args: list = []
    timeout: int = 30


class CodeRun(BaseModel):
    codigo: str
    timeout: int = 15


class CodeTest(BaseModel):
    codigo: str
    framework: str = "pytest"


class CodeDoc(BaseModel):
    codigo: str
    formato: str = "google"


class CodeDiff(BaseModel):
    codigo_antigo: str
    codigo_novo: str


class CodeSQL(BaseModel):
    descricao: str
    dialeto: str = "postgresql"


class CodeRegex(BaseModel):
    descricao: str


class CodeBenchmark(BaseModel):
    codigo: str
    repeticoes: int = 100


class CodeScaffold(BaseModel):
    tipo: str
    nome: str = "meu_projeto"


class YouTubeTranscript(BaseModel):
    url: str
    idiomas: list = ["pt", "en"]


class YouTubeSummarize(BaseModel):
    url: str
    idiomas: list = ["pt", "en"]
    max_pontos: int = 5


class YouTubeAsk(BaseModel):
    url: str
    pergunta: str
    idiomas: list = ["pt", "en"]


class YouTubeSave(BaseModel):
    url: str
    idiomas: list = ["pt", "en"]
    nome: str = ""


class YouTubeList(BaseModel):
    pass


class YouTubeRead(BaseModel):
    video_id: str
    max_chars: int = 5000


class TaskSimple(BaseModel):
    objetivo: str
    max_passos: int = 5


def _contexto_vivo():
    global context, page
    try:
        if context is None or page is None:
            return False
        _ = page.title()
        return True
    except Exception:
        return False


def start_browser():
    global browser, context, page, playwright

    if _contexto_vivo():
        return

    print("[START_BROWSER] contexto morto ou inexistente. Recriando...")

    try:
        if context is not None:
            context.close()
    except Exception as e:
        print(f"[START_BROWSER] context.close ignorado: {e}")
    try:
        if browser is not None:
            browser.close()
    except Exception as e:
        print(f"[START_BROWSER] browser.close ignorado: {e}")
    try:
        if playwright is not None:
            playwright.stop()
    except Exception as e:
        print(f"[START_BROWSER] playwright.stop ignorado: {e}")

    context = None
    browser = None
    page = None
    playwright = None

    try:
        lock_file = os.path.join(PERFIL_DIR, "SingletonLock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("[START_BROWSER] lock file removido")
        for nome in ["SingletonCookie", "SingletonSocket"]:
            p = os.path.join(PERFIL_DIR, nome)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
    except Exception as e:
        print(f"[START_BROWSER] erro ao limpar lock: {e}")

    os.makedirs(PERFIL_DIR, exist_ok=True)

    playwright = sync_playwright().start()

    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=PERFIL_DIR,
            channel="chrome",
            headless=False,
            slow_mo=500,
            viewport={"width": 1280, "height": 800},
            args=[
                "--profile-directory=Default",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        print("[START_BROWSER] usando Chrome real (perfil dedicado)")
    except Exception as e:
        print(f"[START_BROWSER] Chrome real falhou ({e}). Tentando Chromium.")
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=PERFIL_DIR,
                headless=False,
                slow_mo=500,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--profile-directory=Default",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            print("[START_BROWSER] usando Chromium com perfil dedicado")
        except Exception as e2:
            print(f"[START_BROWSER] FALHA TOTAL: {e2}")
            raise

    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});
        window.chrome = {runtime: {}};
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
        );
    """)

    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    print(f"[START_BROWSER] perfil persistente em: {PERFIL_DIR}")


def _detectar_captcha():
    try:
        url = page.url
        conteudo = page.content().lower()
        if "sorry/index" in url or "captcha" in url:
            return True
        if "unusual traffic" in conteudo or "not a robot" in conteudo:
            return True
        if "detectamos um trafego" in conteudo or "confirme que voce" in conteudo:
            return True
        return False
    except Exception:
        return False


def _decodificar(valor):
    if not valor:
        return "(vazio)"
    try:
        partes = decode_header(valor)
        resultado = ""
        for texto, encoding in partes:
            if isinstance(texto, bytes):
                resultado += texto.decode(encoding or "utf-8", errors="ignore")
            else:
                resultado += texto
        return resultado
    except Exception:
        return valor


def _detectar_cidade_por_ip() -> str:
    """Retorna a cidade configurada manualmente."""
    return CIDADE_PADRAO


def _fix_encoding(texto: str) -> str:
    """Corrige encoding bagunçado (UTF-8 interpretado como Latin-1)."""
    if not texto:
        return texto
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            return texto.encode("utf-8").decode("latin-1")
        except Exception:
            return texto


@app.get("/")
def home():
    return {"status": "online", "agent": "computer-agent"}


@app.post("/open_url")
def open_url(data: OpenURL):
    start_browser()
    print(f"[OPEN_URL] url={data.url}")
    try:
        page.goto(data.url, timeout=15000)

        if _detectar_captcha():
            url_lower = data.url.lower()
            if "google.com/search" in url_lower or "google.com.br/search" in url_lower:
                try:
                    parsed = urllib.parse.urlparse(data.url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    termo = qs.get("q", [""])[0]
                    termo = urllib.parse.unquote(termo)
                    if termo:
                        print(f"[OPEN_URL] Google bloqueou. Buscando '{termo}' no DuckDuckGo...")
                        return _buscar_duckduckgo(termo)
                except Exception as e:
                    print(f"[OPEN_URL] erro ao extrair termo: {e}")

            return {"status": "aviso", "result": f"AVISO: CAPTCHA ou bloqueio detectado em {data.url}. Resolva manualmente ou tente outro site."}

        return {"status": "ok", "result": f"Abri {data.url}"}
    except Exception as e:
        print(f"[OPEN_URL] ERRO: {e}")
        return {"status": "erro", "result": f"Falha ao abrir {data.url}: {type(e).__name__}"}


@app.post("/search_google")
def search_google(data: SearchGoogle):
    start_browser()
    print(f"[SEARCH_GOOGLE] query={data.query}")
    try:
        page.goto("https://www.google.com", timeout=15000)

        if _detectar_captcha():
            print("[SEARCH_GOOGLE] CAPTCHA detectado. Tentando DuckDuckGo...")
            return _buscar_duckduckgo(data.query)

        try:
            campo = page.locator("textarea[name='q'], input[name='q']").first
            campo.fill(data.query)
            campo.press("Enter")
            page.wait_for_timeout(5000)

            if _detectar_captcha():
                print("[SEARCH_GOOGLE] CAPTCHA apos busca. Tentando DuckDuckGo...")
                return _buscar_duckduckgo(data.query)

            return {"status": "ok", "result": f"Pesquisei por: {data.query}"}
        except Exception as e:
            print(f"[SEARCH_GOOGLE] erro no campo: {e}. Tentando DuckDuckGo...")
            return _buscar_duckduckgo(data.query)

    except Exception as e:
        print(f"[SEARCH_GOOGLE] ERRO: {e}")
        return {"status": "erro", "result": f"Falha na busca: {type(e).__name__}"}


@app.post("/search_in_page")
def search_in_page(data: SearchGoogle):
    start_browser()
    print(f"[SEARCH_IN_PAGE] query={data.query}")
    try:
        candidatos = [
            page.locator("input[type='search']:visible").first,
            page.locator("input[name='search_query']:visible").first,
            page.locator("input[aria-label*='Search']:visible").first,
            page.locator("input[aria-label*='Pesquisar']:visible").first,
            page.locator("input[placeholder*='Search']:visible").first,
            page.locator("input[placeholder*='Pesquisar']:visible").first,
            page.locator("textarea[name='q']:visible").first,
            page.locator("input[name='q']:visible").first,
        ]

        campo = None
        for c in candidatos:
            try:
                if c.count() > 0:
                    campo = c
                    print("[SEARCH_IN_PAGE] achou barra de pesquisa")
                    break
            except Exception:
                continue

        if campo is None:
            print("[SEARCH_IN_PAGE] fallback: primeiro input visivel")
            inputs = page.locator("input:visible").all()
            for inp in inputs:
                try:
                    tipo = inp.get_attribute("type") or "text"
                    if tipo in ("text", "search", "email"):
                        campo = inp
                        break
                except Exception:
                    pass

        if campo is None:
            return {"status": "erro", "result": "Nao achei barra de pesquisa na pagina atual"}

        campo.click(timeout=5000)
        page.wait_for_timeout(300)
        campo.press("Control+A")
        page.wait_for_timeout(100)
        campo.press("Delete")
        page.wait_for_timeout(300)
        campo.press_sequentially(data.query, delay=60)
        page.wait_for_timeout(500)
        campo.press("Enter")
        page.wait_for_timeout(5000)

        return {"status": "ok", "result": f"Pesquisei '{data.query}' na pagina atual ({page.url})"}
    except Exception as e:
        print(f"[SEARCH_IN_PAGE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}"}


def _buscar_duckduckgo(query: str):
    try:
        page.goto("https://duckduckgo.com", timeout=20000)
        page.wait_for_timeout(2000)

        seletores = [
            "input[name='q']",
            "#searchbox_input",
            "input[type='text']",
            "input[aria-label*='Search']",
            "input[aria-label*='Pesquisar']",
            "textarea[name='q']",
        ]

        campo = None
        for sel in seletores:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    campo = loc
                    print(f"[DUCKDUCKGO] usando seletor: {sel}")
                    break
            except Exception:
                continue

        if campo is None:
            return {"status": "erro", "result": "Nao consegui achar o campo de busca do DuckDuckGo"}

        campo.fill(query)
        campo.press("Enter")
        page.wait_for_timeout(5000)
        return {"status": "ok", "result": f"Google bloqueou. Pesquisei por '{query}' no DuckDuckGo."}
    except Exception as e:
        print(f"[DUCKDUCKGO] ERRO: {e}")
        return {"status": "erro", "result": f"Falha na busca: {type(e).__name__}"}


@app.post("/click_element")
def click_element(data: ClickElement):
    start_browser()
    print(f"[CLICK_ELEMENT] text={data.text!r} selector={data.selector!r}")
    try:
        if data.text:
            loc = page.get_by_text(data.text, exact=False)
            if loc.count() > 0:
                loc.first.click(timeout=15000)
                page.wait_for_timeout(1500)
                return {"status": "ok", "result": f"Cliquei em '{data.text}'. URL: {page.url}"}
            return {"status": "erro", "result": f"Nenhum elemento com texto '{data.text}'"}
        elif data.selector:
            loc = page.locator(data.selector)
            if loc.count() > 0:
                loc.first.click(timeout=15000)
                page.wait_for_timeout(1500)
                return {"status": "ok", "result": f"Cliquei em {data.selector}. URL: {page.url}"}
            return {"status": "erro", "result": f"Nenhum elemento com seletor '{data.selector}'"}
        return {"status": "erro", "result": "Precisa de text ou selector"}
    except Exception as e:
        print(f"[CLICK_ELEMENT] ERRO: {e}")
        return {"status": "erro", "result": f"Erro ao clicar: {type(e).__name__}"}


@app.post("/click_by_description")
def click_by_description(data: ClickElement):
    start_browser()
    print(f"[CLICK_BY_DESCRIPTION] text={data.text!r}")
    try:
        texto_busca = data.text.strip()
        estrategias = []

        estrategias.append(("texto exato", lambda: page.get_by_text(texto_busca, exact=True).first))
        estrategias.append(("texto parcial", lambda: page.get_by_text(texto_busca, exact=False).first))

        match = _re.search(r"\b(\d+)\b", texto_busca)
        if match:
            indice = int(match.group(1))
            if indice > 0:
                estrategias.append((
                    f"link de indice {indice-1}",
                    lambda idx=indice-1: page.locator("a").nth(idx)
                ))

        for role in ["link", "button"]:
            estrategias.append((
                f"role={role}",
                lambda r=role: page.get_by_role(r, name=texto_busca).first
            ))

        palavras = [p for p in texto_busca.split() if len(p) > 2 and not p.isdigit()]
        if palavras:
            palavra = palavras[0]
            estrategias.append((
                f"texto contem '{palavra}'",
                lambda p=palavra: page.get_by_text(p, exact=False).first
            ))

        for nome, fn in estrategias:
            try:
                loc = fn()
                if loc.count() > 0:
                    print(f"[CLICK_BY_DESCRIPTION] tentando: {nome}")
                    loc.click(timeout=8000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)
                    print(f"[CLICK_BY_DESCRIPTION] OK via {nome}. URL: {page.url}")
                    return {"status": "ok", "result": f"Cliquei em '{data.text}' (via {nome}). URL: {page.url}"}
            except Exception:
                continue

        print("[CLICK_BY_DESCRIPTION] nenhuma estrategia funcionou, tentando primeiro link")
        try:
            links = page.locator("a").all()
            if len(links) > 0:
                primeiro = links[0]
                txt = primeiro.inner_text().strip()
                primeiro.click(timeout=15000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)
                return {"status": "ok", "result": f"Cliquei no primeiro link '{txt}'. URL: {page.url}"}
        except Exception as e:
            print(f"[CLICK_BY_DESCRIPTION] erro no fallback: {e}")

        clicaveis = []
        try:
            for i, a in enumerate(page.locator("a").all()[:15]):
                try:
                    txt = a.inner_text().strip()
                    href = a.get_attribute("href") or ""
                    if txt:
                        clicaveis.append(f"[{i}] LINK {txt} -> {href[:80]}")
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "status": "erro",
            "result": f"Nao encontrei nada clicavel com '{data.text}'. Links disponiveis (use o indice ou o texto exato):\n" + "\n".join(clicaveis)
        }
    except Exception as e:
        print(f"[CLICK_BY_DESCRIPTION] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/type_text")
def type_text(data: TypeText):
    start_browser()
    print(f"[TYPE_TEXT] text={data.text!r} field_text={data.field_text!r}")
    try:
        loc = None

        if data.selector:
            loc = page.locator(data.selector).first
        elif data.field_text:
            ft = data.field_text.lower()
            if "senha" in ft or "password" in ft:
                print("[TYPE_TEXT] detectado campo de SENHA")
                loc = page.locator("input[type='password']:visible").first
            elif "email" in ft or "e-mail" in ft or "usuario" in ft or "user" in ft or "phone" in ft or "telefone" in ft:
                print("[TYPE_TEXT] detectado campo de EMAIL/USUARIO")
                loc = page.locator("input[type='email']:visible, input[type='text']:visible").first
            else:
                for tentativa in [
                    lambda: page.get_by_placeholder(data.field_text).first,
                    lambda: page.get_by_label(data.field_text).first,
                    lambda: page.get_by_role("textbox", name=data.field_text).first,
                ]:
                    try:
                        cand = tentativa()
                        if cand.count() > 0:
                            loc = cand
                            break
                    except Exception:
                        continue
        else:
            return {"status": "erro", "result": "Precisa de selector ou field_text"}

        if loc is None:
            return {"status": "erro", "result": f"Nao consegui achar o campo para '{data.field_text}'"}

        loc.click(timeout=5000)
        page.wait_for_timeout(300)
        loc.press("Control+A")
        page.wait_for_timeout(100)
        loc.press("Delete")
        page.wait_for_timeout(300)
        loc.press_sequentially(data.text, delay=80)
        page.wait_for_timeout(500)

        return {"status": "ok", "result": f"Digitei '{data.text}' em '{data.field_text}'"}
    except Exception as e:
        print(f"[TYPE_TEXT] ERRO: {e}")
        return {"status": "erro", "result": f"Erro ao digitar: {type(e).__name__}"}


@app.post("/press_key")
def press_key(data: PressKey):
    start_browser()
    print(f"[PRESS_KEY] key={data.key!r}")
    try:
        page.keyboard.press(data.key)
        return {"status": "ok", "result": f"Pressionei {data.key}"}
    except Exception as e:
        return {"status": "erro", "result": f"Erro: {type(e).__name__}"}


@app.post("/go_back")
def go_back():
    start_browser()
    print("[GO_BACK]")
    try:
        page.go_back(timeout=10000)
        page.wait_for_timeout(1000)
        return {"status": "ok", "result": "Voltei uma pagina"}
    except Exception as e:
        return {"status": "erro", "result": f"Erro: {type(e).__name__}"}


@app.post("/wait")
def wait(data: Wait):
    start_browser()
    print(f"[WAIT] seconds={data.seconds}")
    page.wait_for_timeout(int(data.seconds * 1000))
    return {"status": "ok", "result": f"Esperei {data.seconds}s"}


@app.post("/read_page")
def read_page():
    start_browser()
    print("[READ_PAGE]")
    try:
        texto = page.inner_text("body")[:2000]
    except Exception:
        texto = ""

    clicaveis = []
    vistos = set()

    try:
        for a in page.locator("a").all()[:30]:
            try:
                txt = a.inner_text().strip()
                href = a.get_attribute("href") or ""
                if txt and txt not in vistos:
                    vistos.add(txt)
                    clicaveis.append(f"LINK {txt} -> {href}")
            except Exception:
                pass
    except Exception:
        pass

    try:
        for b in page.locator("button").all()[:20]:
            try:
                txt = b.inner_text().strip()
                if txt and txt not in vistos:
                    vistos.add(txt)
                    clicaveis.append(f"BOTAO {txt}")
            except Exception:
                pass
    except Exception:
        pass

    try:
        for i in page.locator("input, textarea").all()[:15]:
            try:
                ph = i.get_attribute("placeholder") or ""
                nome = i.get_attribute("name") or ""
                tipo = i.get_attribute("type") or "text"
                if ph or nome:
                    info = f"CAMPO placeholder={ph} name={nome} type={tipo}"
                    if info not in vistos:
                        vistos.add(info)
                        clicaveis.append(info)
            except Exception:
                pass
    except Exception:
        pass

    return {"status": "ok", "result": texto, "clicaveis": clicaveis}


@app.post("/request_confirmation")
def request_confirmation(data: Confirmation):
    global pending_confirmation
    print(f"[REQUEST_CONFIRMATION] acao={data.acao!r} detalhes={data.detalhes!r}")

    if pending_confirmation is not None:
        idade = time.time() - pending_confirmation["timestamp"]
        if idade < CONFIRMATION_TIMEOUT:
            acao_pendente = pending_confirmation["acao"]
            detalhes_pendentes = pending_confirmation.get("detalhes", "")
            msg = (
                f"JA EXISTE UMA CONFIRMACAO PENDENTE: {acao_pendente} ({detalhes_pendentes}). "
                f"NAO chame request_confirmation de novo! "
                f"Se o usuario ja respondeu 'sim', chame a ferramenta destrutiva DIRETAMENTE agora "
                f"(email_delete, delete_file, move_file, email_reply ou email_send)."
            )
            print(f"[REQUEST_CONFIRMATION] BLOQUEADO (loop detectado)")
            return {"status": "bloqueado", "result": msg}
        else:
            pending_confirmation = None

    pending_confirmation = {
        "acao": data.acao,
        "detalhes": data.detalhes,
        "timestamp": time.time(),
        "confirmada": False,
        "acao_pendente": data.acao_pendente,
        "parametros": data.parametros,
    }

    msg = f"CONFIRMACAO NECESSARIA: {data.acao}"
    if data.detalhes:
        msg += f" ({data.detalhes})"
    msg += ". Aguardando resposta do usuario (sim/nao)."
    msg += " Quando o usuario responder 'sim', chame a ferramenta destrutiva DIRETAMENTE."
    return {"status": "aguardando", "result": msg}


@app.post("/confirm_action")
def confirm_action():
    global pending_confirmation
    print("[CONFIRM_ACTION]")

    if pending_confirmation is None:
        return {"status": "erro", "result": "Nenhuma acao pendente de confirmacao."}

    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada (mais de 5 minutos). Refaca a solicitacao."}

    pending_confirmation["confirmada"] = True
    acao = pending_confirmation["acao"]
    return {"status": "ok", "result": f"Confirmacao registrada para: {acao}. Agora voce pode executar a acao."}


@app.post("/cancel_confirmation")
def cancel_confirmation():
    global pending_confirmation
    print("[CANCEL_CONFIRMATION]")
    if pending_confirmation is None:
        return {"status": "ok", "result": "Nenhuma acao pendente para cancelar."}
    pending_confirmation = None
    return {"status": "ok", "result": "Confirmacao cancelada."}


@app.post("/confirm_and_execute")
def confirm_and_execute():
    global pending_confirmation
    print("[CONFIRM_AND_EXECUTE]")

    if pending_confirmation is None:
        return {"status": "erro", "result": "Nenhuma acao pendente de confirmacao."}

    if time.time() - pending_confirmation["timestamp"] > CONFIRMATION_TIMEOUT:
        pending_confirmation = None
        return {"status": "erro", "result": "Confirmacao expirada."}

    acao = pending_confirmation.get("acao_pendente", "")
    params = pending_confirmation.get("parametros", {})

    if not acao:
        return {"status": "erro", "result": "Nenhuma acao pendente configurada."}

    print(f"[CONFIRM_AND_EXECUTE] Executando {acao} com {params}")

    try:
        if acao == "email_delete":
            resultado = email_delete(EmailDelete(**params))
        elif acao == "delete_file":
            resultado = delete_file(DeleteFile(**params))
        elif acao == "move_file":
            resultado = move_file(MoveFile(**params))
        elif acao == "email_reply":
            resultado = email_reply(EmailReply(**params))
        elif acao == "email_send":
            resultado = email_send(EmailSend(**params))
        else:
            return {"status": "erro", "result": f"Acao desconhecida: {acao}"}

        pending_confirmation = None
        return resultado
    except Exception as e:
        print(f"[CONFIRM_AND_EXECUTE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro ao executar {acao}: {type(e).__name__}: {e}"}


def _conectar_imap():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise Exception("GMAIL_USER ou GMAIL_APP_PASSWORD nao configurados")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return mail


def _get_trash_folder(mail):
    try:
        status, pastas = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"

        for pasta in pastas:
            nome = pasta.decode("utf-8", errors="ignore")
            if "\\Trash" in nome:
                partes = nome.split('"')
                if len(partes) >= 2:
                    return partes[-2]
        return "[Gmail]/Trash"
    except Exception:
        return "[Gmail]/Trash"


@app.post("/email_list")
def email_list(data: EmailList):
    print(f"[EMAIL_LIST] pasta={data.pasta} quantidade={data.quantidade}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
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
        return {"status": "ok", "result": "\n".join(resultado)}
    except Exception as e:
        print(f"[EMAIL_LIST] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_read")
def email_read(data: EmailRead):
    print(f"[EMAIL_READ] indice={data.indice} pasta={data.pasta}")
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
        msg = email_lib.message_from_bytes(dados[0][1])

        assunto = _decodificar(msg.get("Subject", "(sem assunto)"))
        de = _decodificar(msg.get("From", "(sem remetente)"))

        corpo = ""
        if msg.is_multipart():
            for parte in msg.walk():
                if parte.get_content_type() == "text/plain":
                    corpo = parte.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
        else:
            corpo = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

        mail.logout()
        return {"status": "ok", "result": f"De: {de}\nAssunto: {assunto}\n\n{corpo[:3000]}"}
    except Exception as e:
        print(f"[EMAIL_READ] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_send")
def email_send(data: EmailSend):
    print(f"[EMAIL_SEND] para={data.para!r} assunto={data.assunto!r}")
    try:
        msg = EmailMessage()
        msg["From"] = GMAIL_USER
        msg["To"] = data.para
        msg["Subject"] = data.assunto
        msg.set_content(data.corpo)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)

        return {"status": "ok", "result": f"Email enviado para {data.para}"}
    except Exception as e:
        print(f"[EMAIL_SEND] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_mark_read")
def email_mark_read(data: EmailMark):
    print(f"[EMAIL_MARK_READ] indice={data.indice}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "+FLAGS", "\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_READ] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_mark_unread")
def email_mark_unread(data: EmailMark):
    print(f"[EMAIL_MARK_UNREAD] indice={data.indice}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "-FLAGS", "\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como NAO lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_UNREAD] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_move")
def email_move(data: EmailMove):
    print(f"[EMAIL_MOVE] indice={data.indice}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta_origem)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, data.pasta_destino)
        mail.store(eid, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} movido para {data.pasta_destino}"}
    except Exception as e:
        print(f"[EMAIL_MOVE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_delete")
def email_delete(data: EmailDelete):
    print(f"[EMAIL_DELETE] indice={data.indice}")
    try:
        mail = _conectar_imap()
        trash = _get_trash_folder(mail)
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, trash)
        mail.store(eid, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} movido para a Lixeira"}
    except Exception as e:
        print(f"[EMAIL_DELETE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_search")
def email_search(data: EmailSearch):
    print(f"[EMAIL_SEARCH] termo={data.termo!r}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
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
        return {"status": "ok", "result": "\n".join(resultado)}
    except Exception as e:
        print(f"[EMAIL_SEARCH] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_reply")
def email_reply(data: EmailReply):
    print(f"[EMAIL_REPLY] indice={data.indice}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}

        eid = ids_recentes[data.indice]
        status, dados = mail.fetch(eid, "(RFC822)")
        msg_original = email_lib.message_from_bytes(dados[0][1])

        assunto_original = _decodificar(msg_original.get("Subject", ""))
        de_original = msg_original.get("From", "")
        message_id_original = msg_original.get("Message-ID", "")

        mail.logout()

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

        return {"status": "ok", "result": f"Resposta enviada para {de_original}"}
    except Exception as e:
        print(f"[EMAIL_REPLY] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/get_current_time")
def get_current_time():
    print("[GET_CURRENT_TIME]")
    agora = datetime.datetime.now()
    dias = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    dia_semana = dias[agora.weekday()]
    resultado = agora.strftime(f"%d/%m/%Y %H:%M:%S ({dia_semana})")
    return {"status": "ok", "result": resultado}


@app.post("/save_note")
def save_note(data: SaveNote):
    print(f"[SAVE_NOTE] texto={data.texto[:80]!r}")
    try:
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(NOTES_FILE, "a", encoding="utf-8-sig") as f:
            f.write(f"[{agora}] {data.texto}\n")
        return {"status": "ok", "result": f"Nota salva em {NOTES_FILE}"}
    except Exception as e:
        print(f"[SAVE_NOTE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/read_notes")
def read_notes():
    print("[READ_NOTES]")
    try:
        if not os.path.exists(NOTES_FILE):
            return {"status": "ok", "result": "(nenhuma nota salva ainda)"}
        with open(NOTES_FILE, "r", encoding="utf-8-sig") as f:
            conteudo = f.read()
        if not conteudo.strip():
            return {"status": "ok", "result": "(nenhuma nota salva ainda)"}
        return {"status": "ok", "result": conteudo[-3000:]}
    except Exception as e:
        print(f"[READ_NOTES] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/get_weather")
def get_weather(data: GetWeather):
    cidade = data.cidade.strip() if data.cidade else ""
    if not cidade:
        cidade = _detectar_cidade_por_ip()
    print(f"[GET_WEATHER] cidade={cidade}")
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(cidade)}&count=1&language=pt&format=json"
        with urllib.request.urlopen(geo_url, timeout=10) as r:
            geo = json.loads(r.read().decode())

        if not geo.get("results"):
            return {"status": "erro", "result": f"Cidade '{cidade}' nao encontrada"}

        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]
        nome = geo["results"][0]["name"]
        pais = geo["results"][0].get("country", "")

        clima_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        with urllib.request.urlopen(clima_url, timeout=10) as r:
            clima = json.loads(r.read().decode())

        atual = clima["current"]
        temp = atual["temperature_2m"]
        umid = atual["relative_humidity_2m"]
        vento = atual["wind_speed_10m"]
        codigo = atual["weather_code"]

        codigos = {
            0: "ceu limpo", 1: "poucas nuvens", 2: "parcialmente nublado", 3: "nublado",
            45: "nevoeiro", 48: "nevoeiro com geada",
            51: "chuvisco leve", 53: "chuvisco moderado", 55: "chuvisco denso",
            61: "chuva leve", 63: "chuva moderada", 65: "chuva forte",
            71: "neve leve", 73: "neve moderada", 75: "neve forte",
            80: "pancadas de chuva leve", 81: "pancadas de chuva moderada", 82: "pancadas de chuva forte",
            95: "trovoada", 96: "trovoada com granizo leve", 99: "trovoada com granizo forte",
        }
        descricao = codigos.get(codigo, f"codigo {codigo}")

        resultado = f"{nome}, {pais}: {temp}C, {descricao}, umidade {umid}%, vento {vento} km/h"
        return {"status": "ok", "result": resultado}
    except Exception as e:
        print(f"[GET_WEATHER] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/run_python")
def run_python(data: RunPython):
    print(f"[RUN_PYTHON] codigo={data.codigo[:80]!r}")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(data.codigo)
            arquivo = f.name

        resultado = subprocess.run(
            ["python", arquivo],
            capture_output=True,
            text=True,
            timeout=15,
        )

        os.unlink(arquivo)

        saida = resultado.stdout[:3000] if resultado.stdout else ""
        erro = resultado.stderr[:1000] if resultado.stderr else ""

        if erro and not saida:
            return {"status": "erro", "result": f"ERRO:\n{erro}"}

        return {"status": "ok", "result": saida + (f"\n(stderr: {erro})" if erro else "")}
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": "Timeout: codigo demorou mais de 15 segundos"}
    except Exception as e:
        print(f"[RUN_PYTHON] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/list_dir")
def list_dir(data: ListDir):
    print(f"[LIST_DIR] caminho={data.caminho}")
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)

        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        if not os.path.exists(caminho_completo):
            return {"status": "erro", "result": f"Caminho nao encontrado: {data.caminho}"}

        itens = []
        for item in os.listdir(caminho_completo):
            item_path = os.path.join(caminho_completo, item)
            tipo = "DIR" if os.path.isdir(item_path) else "FILE"
            tamanho = os.path.getsize(item_path) if os.path.isfile(item_path) else 0
            itens.append(f"{tipo}: {item} ({tamanho} bytes)")

        return {"status": "ok", "result": "\n".join(itens) if itens else "(pasta vazia)"}
    except Exception as e:
        print(f"[LIST_DIR] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/read_file")
def read_file(data: ReadFile):
    print(f"[READ_FILE] caminho={data.caminho}")
    try:
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)
        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        if not os.path.exists(caminho_completo):
            return {"status": "erro", "result": f"Arquivo nao encontrado: {data.caminho}"}

        if not os.path.isfile(caminho_completo):
            return {"status": "erro", "result": f"Nao e um arquivo: {data.caminho}"}

        with open(caminho_completo, "r", encoding="utf-8-sig") as f:
            conteudo = f.read()

        return {"status": "ok", "result": conteudo[:4000]}
    except Exception as e:
        print(f"[READ_FILE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/write_file")
def write_file(data: WriteFile):
    print(f"[WRITE_FILE] caminho={data.caminho}")
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        caminho_completo = os.path.join(WORKSPACE_DIR, data.caminho)
        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(WORKSPACE_DIR)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace"}

        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)

        with open(caminho_completo, "w", encoding="utf-8-sig") as f:
            f.write(data.conteudo)

        return {"status": "ok", "result": f"Arquivo salvo: {data.caminho} ({len(data.conteudo)} bytes)"}
    except Exception as e:
        print(f"[WRITE_FILE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/web_search")
def web_search(data: WebSearch):
    print(f"[WEB_SEARCH] query={data.query!r}")
    try:
        import urllib.parse as _urlparse

        url = "https://html.duckduckgo.com/html/"
        payload = _urlparse.urlencode({"q": data.query}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")

        resultados = []
        padrao = _re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            _re.DOTALL,
        )

        for i, match in enumerate(padrao.finditer(html)):
            if i >= data.max_resultados:
                break
            link = match.group(1)
            titulo = _re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = _re.sub(r"<[^>]+>", "", match.group(3)).strip()

            titulo = titulo.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
            snippet = snippet.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')

            if "uddg=" in link:
                parsed = _urlparse.parse_qs(_urlparse.urlparse(link).query)
                if "uddg" in parsed:
                    link = parsed["uddg"][0]

            resultados.append(f"[{i+1}] {titulo}\n    URL: {link}\n    {snippet[:200]}")

        if not resultados:
            return {"status": "erro", "result": "Nenhum resultado encontrado"}

        return {"status": "ok", "result": "\n\n".join(resultados)}
    except Exception as e:
        print(f"[WEB_SEARCH] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/screenshot")
def screenshot():
    start_browser()
    print("[SCREENSHOT]")
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = os.path.join(SCREENSHOTS_DIR, f"screenshot_{agora}.png")

        page.screenshot(path=arquivo, full_page=False)
        print(f"[SCREENSHOT] salvo em {arquivo}")

        tamanho = os.path.getsize(arquivo)
        return {
            "status": "ok",
            "result": f"Screenshot salvo em {arquivo} ({tamanho} bytes)",
            "arquivo": arquivo,
        }
    except Exception as e:
        print(f"[SCREENSHOT] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/see")
def see(data: SeeImage):
    print("[SEE] analisando tela do PC...")
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

        resultado = _pc_screenshot_fn(salvar=True)
        if resultado.get("status") != "ok":
            return {"status": "erro", "result": f"Falha ao capturar tela: {resultado.get('result')}"}

        arquivo = resultado.get("path")
        if not arquivo or not os.path.exists(arquivo):
            return {"status": "erro", "result": "Screenshot nao foi salvo corretamente"}

        print(f"[SEE] screenshot do PC salvo em {arquivo}")

        import base64 as _base64
        with open(arquivo, "rb") as f:
            img_b64 = _base64.b64encode(f.read()).decode()

        payload = {
            "model": "Qwen3.5-0.8B",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": data.pergunta},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                    ]
                }
            ],
            "max_tokens": 500,
        }

        req = urllib.request.Request(
            LLM_EYES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as r:
            resposta = json.loads(r.read().decode("utf-8"))

        msg = resposta["choices"][0]["message"]
        conteudo = msg.get("content", "") or msg.get("reasoning_content", "")

        if conteudo:
            substituicoes = {
                "Ã©": "é", "Ã¡": "á", "Ã£": "ã", "Ã¢": "â", "Ãª": "ê",
                "Ã": "í", "Ã³": "ó", "Ã´": "ô", "Ãµ": "õ", "Ãº": "ú",
                "Ã¼": "ü", "Ã§": "ç", "Ã±": "ñ",
            }
            for errado, certo in substituicoes.items():
                conteudo = conteudo.replace(errado, certo)

        print(f"[SEE] resposta: {conteudo[:100]}...")
        return {"status": "ok", "result": conteudo, "screenshot": arquivo}
    except Exception as e:
        print(f"[SEE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


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
    print(f"[SEARCH_IN_FILES] termo={data.termo!r}")
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

        return {"status": "ok", "result": f"{len(resultados)} ocorrencia(s):\n" + "\n".join(resultados)}
    except Exception as e:
        print(f"[SEARCH_IN_FILES] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_delete_by_search")
def email_delete_by_search(data: EmailDeleteBySearch):
    print(f"[EMAIL_DELETE_BY_SEARCH] termo={data.termo!r}")
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
                mail.store(eid, "+FLAGS", "\\Deleted")
                apagados += 1
            except Exception:
                pass

        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"{apagados} email(s) com {data.termo!r} movidos para a Lixeira"}
    except Exception as e:
        print(f"[EMAIL_DELETE_BY_SEARCH] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


from computer.controller import (
    move_mouse as _pc_move_mouse,
    click as _pc_click_fn,
    double_click as _pc_double_click_fn,
    right_click as _pc_right_click_fn,
    type_text as _pc_type_text_fn,
    press_key as _pc_press_key_fn,
    hotkey as _pc_hotkey_fn,
    scroll as _pc_scroll_fn,
)
from computer.screen import screenshot as _pc_screenshot_fn
from computer.windows import (
    get_windows as _pc_get_windows,
    get_active_window as _pc_get_active_window,
    focus_window as _pc_focus_window,
)


@app.post("/pc_move_mouse")
def pc_move_mouse(data: PCMoveMouse):
    print(f"[PC_MOVE_MOUSE] x={data.x} y={data.y}")
    return _pc_move_mouse(data.x, data.y, data.duration)


@app.post("/pc_click")
def pc_click(data: PCClick):
    print(f"[PC_CLICK] x={data.x} y={data.y} button={data.button}")
    return _pc_click_fn(data.x, data.y, data.button)


@app.post("/pc_double_click")
def pc_double_click(data: PCClickXY):
    print(f"[PC_DOUBLE_CLICK] x={data.x} y={data.y}")
    return _pc_double_click_fn(data.x, data.y)


@app.post("/pc_right_click")
def pc_right_click(data: PCClickXY):
    print(f"[PC_RIGHT_CLICK] x={data.x} y={data.y}")
    return _pc_right_click_fn(data.x, data.y)


@app.post("/pc_type_text")
def pc_type_text(data: PCTypeText):
    print(f"[PC_TYPE_TEXT] len={len(data.text)}")
    return _pc_type_text_fn(data.text, data.interval)


@app.post("/pc_press_key")
def pc_press_key(data: PCPressKey):
    print(f"[PC_PRESS_KEY] key={data.key}")
    return _pc_press_key_fn(data.key)


@app.post("/pc_hotkey")
def pc_hotkey(data: PCHotkey):
    print(f"[PC_HOTKEY] keys={data.keys}")
    return _pc_hotkey_fn(*data.keys)


@app.post("/pc_scroll")
def pc_scroll(data: PCScroll):
    print(f"[PC_SCROLL] amount={data.amount}")
    return _pc_scroll_fn(data.amount)


@app.post("/pc_screenshot")
def pc_screenshot(data: PCScreenshot = None):
    salvar = data.salvar if data else True
    print(f"[PC_SCREENSHOT] salvar={salvar}")
    return _pc_screenshot_fn(salvar)


@app.post("/pc_get_windows")
def pc_get_windows():
    print("[PC_GET_WINDOWS]")
    return _pc_get_windows()


@app.post("/pc_get_active_window")
def pc_get_active_window():
    print("[PC_GET_ACTIVE_WINDOW]")
    return _pc_get_active_window()


@app.post("/pc_focus_window")
def pc_focus_window(data: PCFocusWindow):
    print(f"[PC_FOCUS_WINDOW] titulo={data.titulo}")
    return _pc_focus_window(data.titulo)


def _owui_request(method: str, path: str, json_body: dict = None):
    url = f"{OPENWEBUI_URL}{path}"
    headers = {
        "Authorization": f"Bearer {OPENWEBUI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps(json_body).encode() if json_body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return {"ok": True, "data": json.loads(body) if body else None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@app.post("/pc_get_chats")
def pc_get_chats(data: ChatList):
    global _chat_cache
    print(f"[PC_GET_CHATS] quantidade={data.quantidade}")

    agora = time.time()
    if _chat_cache["data"] is None or (agora - _chat_cache["timestamp"]) > CHAT_CACHE_TTL:
        r = _owui_request("GET", "/api/v1/chats/")
        if not r["ok"]:
            return {"status": "erro", "result": f"Erro ao listar: {r.get('error')}"}
        _chat_cache["data"] = r["data"]
        _chat_cache["timestamp"] = agora
        print(f"[PC_GET_CHATS] cache atualizado ({len(r['data'])} chats)")
    else:
        print(f"[PC_GET_CHATS] usando cache")

    chats = _chat_cache["data"][:data.quantidade]
    titulos = []
    for c in chats:
        titulos.append(_fix_encoding(c['title'])[:60])
    texto = "\n".join(titulos) if titulos else "(nenhum chat)"
    return {"status": "ok", "result": texto}


@app.post("/pc_remove_chat")
def pc_remove_chat(data: ChatDelete):
    global _chat_cache
    print(f"[PC_REMOVE_CHAT] indice={data.indice} chat_id={data.chat_id}")

    if data.chat_id:
        cid = data.chat_id
    else:
        r = _owui_request("GET", "/api/v1/chats/")
        if not r["ok"]:
            return {"status": "erro", "result": f"Erro ao listar: {r.get('error')}"}
        chats = r["data"]
        if data.indice >= len(chats):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(chats)})"}
        cid = chats[data.indice]["id"]

    r = _owui_request("DELETE", f"/api/v1/chats/{cid}")
    if not r["ok"]:
        return {"status": "erro", "result": f"Erro ao apagar: {r.get('error')}"}
    _chat_cache["data"] = None
    return {"status": "ok", "result": f"Chat apagado: {cid[:8]}..."}


@app.post("/pc_remove_chats_by_search")
def pc_remove_chats_by_search(data: ChatDeleteBySearch):
    global _chat_cache
    print(f"[PC_REMOVE_CHATS_BY_SEARCH] termo={data.termo!r} limite={data.limite}")
    r = _owui_request("GET", "/api/v1/chats/")
    if not r["ok"]:
        return {"status": "erro", "result": f"Erro ao listar: {r.get('error')}"}

    termo_lower = data.termo.lower()
    alvos = [c for c in r["data"] if termo_lower in _fix_encoding(c["title"]).lower()][:data.limite]

    if not alvos:
        return {"status": "ok", "result": f"Nenhum chat com {data.termo!r}"}

    apagados = 0
    for c in alvos:
        rr = _owui_request("DELETE", f"/api/v1/chats/{c['id']}")
        if rr["ok"]:
            apagados += 1

    _chat_cache["data"] = None
    return {"status": "ok", "result": f"{apagados} chat(s) apagados (busca: {data.termo!r})"}


@app.post("/pc_remove_all_chats")
def pc_remove_all_chats(data: ChatDeleteAll):
    global _chat_cache
    print(f"[PC_REMOVE_ALL_CHATS] confirmar={data.confirmar}")

    if not data.confirmar:
        return {"status": "erro", "result": "ATENCAO: para apagar TODOS os chats, chame de novo com confirmar=true"}

    r = _owui_request("GET", "/api/v1/chats/")
    if not r["ok"]:
        return {"status": "erro", "result": f"Erro ao listar: {r.get('error')}"}

    apagados = 0
    for c in r["data"]:
        rr = _owui_request("DELETE", f"/api/v1/chats/{c['id']}")
        if rr["ok"]:
            apagados += 1

    _chat_cache["data"] = None
    return {"status": "ok", "result": f"{apagados} chat(s) apagados (TODOS)"}


@app.post("/pc_rename_chat")
def pc_rename_chat(data: ChatRename):
    global _chat_cache
    print(f"[PC_RENAME_CHAT] indice={data.indice} novo={data.novo_titulo!r}")

    if data.chat_id:
        cid = data.chat_id
    else:
        r = _owui_request("GET", "/api/v1/chats/")
        if not r["ok"]:
            return {"status": "erro", "result": f"Erro ao listar: {r.get('error')}"}
        chats = r["data"]
        if data.indice >= len(chats):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range"}
        cid = chats[data.indice]["id"]

    r_get = _owui_request("GET", f"/api/v1/chats/{cid}")
    if not r_get["ok"] or not r_get.get("data"):
        return {"status": "erro", "result": f"Erro ao carregar chat: {r_get.get('error')}"}

    chat_obj = r_get["data"]

    if "chat" in chat_obj and isinstance(chat_obj["chat"], dict):
        chat_obj["chat"]["title"] = data.novo_titulo
    chat_obj["title"] = data.novo_titulo

    payload = {"chat": chat_obj.get("chat", chat_obj), "title": data.novo_titulo}

    r_post = _owui_request("POST", f"/api/v1/chats/{cid}", payload)
    if not r_post["ok"]:
        return {"status": "erro", "result": f"Erro ao renomear: {r_post.get('error')}"}
    _chat_cache["data"] = None
    return {"status": "ok", "result": f"Chat renomeado para {data.novo_titulo!r}"}


CODE_MODEL_PRIMARY = "R4C3R/qwen2.5-coder-3b-heretic:latest"
CODE_MODEL_FALLBACK = "qwen2.5-coder:7b"
CODE_WORKSPACE = os.path.join(WORKSPACE_DIR, "code")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def _llm_generate(prompt: str, system: str = "") -> dict:
    modelos = [CODE_MODEL_PRIMARY, CODE_MODEL_FALLBACK]

    for modelo in modelos:
        try:
            payload = {
                "model": modelo,
                "prompt": prompt,
                "system": system or "Voce e um programador senior. Responda com codigo limpo e comentado em portugues.",
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 8192},
            }
            req = urllib.request.Request(
                OLLAMA_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                resposta = json.loads(r.read().decode())
                texto = resposta.get("response", "")
                if texto:
                    return {"status": "ok", "result": texto, "modelo_usado": modelo}
        except Exception as e:
            print(f"[LLM_GENERATE] modelo {modelo} falhou: {e}")
            continue

    return {"status": "erro", "result": "Nenhum modelo disponivel. Rode 'ollama pull qwen2.5-coder:7b'"}


@app.post("/code_generate")
def code_generate(data: CodeGenerate):
    print(f"[CODE_GENERATE] {data.linguagem}: {data.descricao[:80]}")
    prompt = f"Crie um codigo {data.linguagem} que faca o seguinte:\n\n{data.descricao}\n\nResponda APENAS com o codigo, sem explicacoes antes ou depois."
    return _llm_generate(prompt)


@app.post("/code_explain")
def code_explain(data: CodeInput):
    print(f"[CODE_EXPLAIN] len={len(data.codigo)}")
    prompt = f"Explique o seguinte codigo de forma clara e didatica, linha por linha quando relevante:\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_analyze")
def code_analyze(data: CodeInput):
    print(f"[CODE_ANALYZE] len={len(data.codigo)}")
    prompt = f"Analise o codigo abaixo e identifique:\n1. Bugs ou erros logicos\n2. Problemas de seguranca\n3. Problemas de performance\n4. Boas praticas violadas\n5. Sugestoes de melhoria\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_review")
def code_review(data: CodeInput):
    print(f"[CODE_REVIEW] len={len(data.codigo)}")
    prompt = f"Faca um code review profissional do codigo abaixo. Aponte pontos fortes e fracos, sugira melhorias com exemplos.\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_refactor")
def code_refactor(data: CodeRefactor):
    print(f"[CODE_REFACTOR] objetivo={data.objetivo[:80]}")
    prompt = f"Refatore o codigo abaixo com o seguinte objetivo: {data.objetivo}\n\n```\n{data.codigo}\n```\n\nResponda com o codigo refatorado e uma breve explicacao das mudancas."
    return _llm_generate(prompt)


@app.post("/code_optimize")
def code_optimize(data: CodeInput):
    print(f"[CODE_OPTIMIZE] len={len(data.codigo)}")
    prompt = f"Otimize o codigo abaixo para melhor performance, mantendo o comportamento. Explique as otimizacoes.\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_convert")
def code_convert(data: CodeConvert):
    print(f"[CODE_CONVERT] {data.linguagem_origem} -> {data.linguagem_destino}")
    prompt = f"Converta o codigo {data.linguagem_origem} abaixo para {data.linguagem_destino}, mantendo a funcionalidade:\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_test")
def code_test(data: CodeTest):
    print(f"[CODE_TEST] framework={data.framework}")
    prompt = f"Crie testes unitarios usando {data.framework} para o codigo abaixo. Cubra casos normais, extremos e de erro.\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_document")
def code_document(data: CodeDoc):
    print(f"[CODE_DOCUMENT] formato={data.formato}")
    prompt = f"Adicione documentacao no formato {data.formato} (docstrings e comentarios) ao codigo abaixo, sem alterar a logica:\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_diff")
def code_diff(data: CodeDiff):
    print("[CODE_DIFF]")
    prompt = f"Compare os dois codigos abaixo e explique as diferencas:\n\n=== ANTES ===\n```\n{data.codigo_antigo}\n```\n\n=== DEPOIS ===\n```\n{data.codigo_novo}\n```"
    return _llm_generate(prompt)


@app.post("/code_sql")
def code_sql(data: CodeSQL):
    print(f"[CODE_SQL] dialeto={data.dialeto}")
    prompt = f"Crie uma query SQL ({data.dialeto}) para:\n\n{data.descricao}\n\nExplique brevemente a query."
    return _llm_generate(prompt)


@app.post("/code_regex")
def code_regex(data: CodeRegex):
    print(f"[CODE_REGEX] descricao={data.descricao[:80]}")
    prompt = f"Crie uma expressao regular (regex) que atenda a seguinte descricao:\n\n{data.descricao}\n\nExplique cada parte da regex."
    return _llm_generate(prompt)


@app.post("/code_scaffold")
def code_scaffold(data: CodeScaffold):
    print(f"[CODE_SCAFFOLD] tipo={data.tipo} nome={data.nome}")
    prompt = f"Crie a estrutura inicial (scaffold) de um projeto do tipo '{data.tipo}' chamado '{data.nome}'. Liste os arquivos necessarios e o conteudo de cada um."
    return _llm_generate(prompt)


@app.post("/code_run")
def code_run(data: CodeRun):
    print(f"[CODE_RUN] len={len(data.codigo)} timeout={data.timeout}")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(data.codigo)
            arquivo = f.name

        resultado = subprocess.run(
            ["python", arquivo],
            capture_output=True,
            text=True,
            timeout=data.timeout,
        )

        os.unlink(arquivo)

        saida = resultado.stdout[:5000] if resultado.stdout else ""
        erro = resultado.stderr[:2000] if resultado.stderr else ""
        exit_code = resultado.returncode

        partes = [f"EXIT CODE: {exit_code}"]
        if saida:
            partes.append(f"STDOUT:\n{saida}")
        if erro:
            partes.append(f"STDERR:\n{erro}")

        return {
            "status": "ok" if exit_code == 0 else "erro",
            "result": "\n\n".join(partes),
        }
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": f"Timeout: codigo demorou mais de {data.timeout}s"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/code_run_file")
def code_run_file(data: CodeRunFile):
    print(f"[CODE_RUN_FILE] {data.caminho}")
    try:
        os.makedirs(CODE_WORKSPACE, exist_ok=True)
        caminho_completo = os.path.join(CODE_WORKSPACE, data.caminho)

        if not os.path.abspath(caminho_completo).startswith(os.path.abspath(CODE_WORKSPACE)):
            return {"status": "erro", "result": "Acesso negado: fora do workspace de codigo"}

        if not os.path.exists(caminho_completo):
            return {"status": "erro", "result": f"Arquivo nao encontrado: {data.caminho}"}

        cmd = ["python", caminho_completo] + data.args
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=data.timeout)

        saida = resultado.stdout[:5000] if resultado.stdout else ""
        erro = resultado.stderr[:2000] if resultado.stderr else ""

        partes = [f"EXIT CODE: {resultado.returncode}"]
        if saida:
            partes.append(f"STDOUT:\n{saida}")
        if erro:
            partes.append(f"STDERR:\n{erro}")

        return {"status": "ok" if resultado.returncode == 0 else "erro", "result": "\n\n".join(partes)}
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": f"Timeout: {data.timeout}s"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/code_benchmark")
def code_benchmark(data: CodeBenchmark):
    print(f"[CODE_BENCHMARK] repeticoes={data.repeticoes}")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(data.codigo)
            arquivo = f.name

        tempos = []
        for _ in range(min(data.repeticoes, 1000)):
            inicio = time.time()
            subprocess.run(["python", arquivo], capture_output=True, timeout=30)
            tempos.append(time.time() - inicio)

        os.unlink(arquivo)

        if not tempos:
            return {"status": "erro", "result": "Nenhuma execucao completada"}

        media = sum(tempos) / len(tempos)
        minimo = min(tempos)
        maximo = max(tempos)

        resultado = (
            f"Execucoes: {len(tempos)}\n"
            f"Media: {media*1000:.2f}ms\n"
            f"Minimo: {minimo*1000:.2f}ms\n"
            f"Maximo: {maximo*1000:.2f}ms"
        )
        return {"status": "ok", "result": resultado}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/code_dependencies")
def code_dependencies(data: CodeInput):
    print(f"[CODE_DEPENDENCIES] len={len(data.codigo)}")
    prompt = f"Analise o codigo abaixo e liste TODAS as dependencias externas necessarias (bibliotecas, modulos, pacotes). Formato: lista com comando 'pip install' pronto.\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_snippet")
def code_snippet(data: CodeGenerate):
    print(f"[CODE_SNIPPET] {data.descricao[:80]}")
    prompt = f"Crie um pequeno trecho de codigo {data.linguagem} pronto para colar que: {data.descricao}\n\nResponda APENAS com o codigo."
    return _llm_generate(prompt)


@app.post("/code_readme")
def code_readme(data: CodeInput):
    print(f"[CODE_README] len={len(data.codigo)}")
    prompt = f"Gere um arquivo README.md profissional para o seguinte codigo:\n\n```\n{data.codigo}\n```"
    return _llm_generate(prompt)


@app.post("/code_metrics")
def code_metrics(data: CodeInput):
    print(f"[CODE_METRICS] len={len(data.codigo)}")
    linhas = data.codigo.split("\n")
    total_linhas = len(linhas)
    linhas_vazias = sum(1 for l in linhas if not l.strip())
    linhas_comentario = sum(1 for l in linhas if l.strip().startswith("#"))
    linhas_codigo = total_linhas - linhas_vazias - linhas_comentario
    caracteres = len(data.codigo)

    resultado = (
        f"Total de linhas: {total_linhas}\n"
        f"Linhas de codigo: {linhas_codigo}\n"
        f"Linhas em branco: {linhas_vazias}\n"
        f"Linhas de comentario: {linhas_comentario}\n"
        f"Total de caracteres: {caracteres}"
    )
    return {"status": "ok", "result": resultado}


@app.post("/code_lint")
def code_lint(data: CodeInput):
    print(f"[CODE_LINT] len={len(data.codigo)}")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(data.codigo)
            arquivo = f.name

        resultado = subprocess.run(["python", "-m", "py_compile", arquivo], capture_output=True, text=True, timeout=10)
        os.unlink(arquivo)

        if resultado.returncode == 0:
            return {"status": "ok", "result": "OK - Sem erros de sintaxe."}
        else:
            return {"status": "erro", "result": f"Erros encontrados:\n{resultado.stderr[:2000]}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


# ============================================================
# YOUTUBE — FASE 20.1: deteccao automatica de idioma via yt-dlp
# ============================================================

YOUTUBE_ID_REGEX = _re.compile(r"(?:v=|youtu\.be/|youtube\.com/embed/|shorts/)([A-Za-z0-9_-]{11})")
YOUTUBE_WORKSPACE = os.path.join(WORKSPACE_DIR, "youtube")

# Idiomas preferidos por padrao (pt primeiro, depois en, depois os mais comuns)
YOUTUBE_LANGS_PADRAO = ["pt", "en", "es", "fr", "de", "it", "ja", "ko", "zh", "ru", "ar", "hi"]


def _yt_extract_video_id(url_or_id: str) -> str:
    candidate = url_or_id.strip()
    if len(candidate) == 11 and _re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate
    match = YOUTUBE_ID_REGEX.search(candidate)
    if not match:
        raise ValueError("Nao consegui extrair o video ID da URL/ID fornecida.")
    return match.group(1)


def _yt_probe_langs(url: str) -> dict:
    """
    Descobre quais idiomas de legenda existem para o video, SEM baixar nada.
    Retorna {"ok": bool, "manual": [lista], "auto": [lista], "error": str|None}
    """
    probe_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "sleep_requests": 1,
    }
    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"ok": False, "manual": [], "auto": [],
                "error": f"Falha ao sondar legendas: {type(e).__name__}: {e}"}

    if not info:
        return {"ok": False, "manual": [], "auto": [], "error": "extract_info retornou vazio"}

    manual_raw = info.get("subtitles") or {}
    auto_raw = info.get("automatic_captions") or {}

    # Remove "live_chat" (nao e legenda de verdade)
    manual = [l for l in manual_raw.keys() if l != "live_chat"]
    auto = [l for l in auto_raw.keys() if l != "live_chat"]

    return {"ok": True, "manual": manual, "auto": auto, "error": None}


def _yt_escolher_idioma(disponiveis_manual: list, disponiveis_auto: list, preferidos: list):
    """
    Escolhe o idioma a usar. Prioriza preferidos, manual antes de auto.
    Retorna (idioma, source) ou (None, None) se nao houver nada.
    """
    for lang in preferidos:
        # match exato ou prefixo (pt casa com pt-BR, pt-PT, pt-orig)
        for m in disponiveis_manual:
            if m == lang or m.startswith(lang + "-"):
                return m, "manual"
        for a in disponiveis_auto:
            if a == lang or a.startswith(lang + "-"):
                return a, "auto"

    # Nenhum preferido disponivel: pega o primeiro que houver
    if disponiveis_manual:
        return disponiveis_manual[0], "manual"
    if disponiveis_auto:
        return disponiveis_auto[0], "auto"

    return None, None


def _yt_download_transcript(url: str, idiomas: list = None) -> dict:
    """
    Baixa a transcricao de um video via yt-dlp (biblioteca Python).
    Detecta automaticamente os idiomas disponiveis ANTES de tentar baixar.

    Retorna dict padronizado:
      {"status": "ok", "video_id", "idioma", "source", "full_text", "total_caracteres"}
      ou {"status": "erro", "result": "msg"}
    """
    video_id = _yt_extract_video_id(url)

    # 1) Lista de preferencia: se o usuario passou, usa; senao, usa o padrao
    if idiomas:
        preferidos = list(idiomas)
        # completa com o padrao (sem duplicar) para ter fallback
        for l in YOUTUBE_LANGS_PADRAO:
            if l not in preferidos:
                preferidos.append(l)
    else:
        preferidos = list(YOUTUBE_LANGS_PADRAO)

    # 2) SONDAGEM — descobre o que existe
    probe = _yt_probe_langs(url)
    if not probe["ok"]:
        return {"status": "erro", "result": probe["error"]}

    manual = probe["manual"]
    auto = probe["auto"]

    if not manual and not auto:
        return {
            "status": "erro",
            "result": (
                "Este video NAO tem nenhuma legenda disponivel "
                "(nem manual, nem automatica). "
                "Numa fase futura (FASE 20.5) podemos usar Whisper "
                "para transcrever o audio."
            ),
        }

    # 3) ESCOLHA do idioma
    idioma_escolhido, source = _yt_escolher_idioma(manual, auto, preferidos)
    if not idioma_escolhido:
        return {
            "status": "erro",
            "result": "Nenhuma legenda utilizavel encontrada para este video.",
        }

    print(f"[YT] video={video_id} manual={manual} auto={auto} escolhido={idioma_escolhido} ({source})")

    # 4) DOWNLOAD no idioma escolhido
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = os.path.join(tmpdir, f"yt_{video_id}")

        dl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [idioma_escolhido],
            "subtitlesformat": "vtt",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "sleep_requests": 1,
            "extractor_retries": 3,
        }

        try:
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            return {
                "status": "erro",
                "result": f"Falha ao baixar legenda [{idioma_escolhido}]: {type(e).__name__}: {e}",
            }

        # 5) Procura o .vtt baixado
        arquivos_vtt = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not arquivos_vtt:
            return {
                "status": "erro",
                "result": (
                    f"Baixou mas nao achou .vtt (idioma {idioma_escolhido}). "
                    "Talvez o YouTube tenha retornado vazio (429?)."
                ),
            }

        # Escolhe o .vtt cujo nome contem o idioma escolhido; senao, o primeiro
        arquivo_escolhido = None
        for arq in arquivos_vtt:
            if f".{idioma_escolhido}." in arq:
                arquivo_escolhido = arq
                break
        if not arquivo_escolhido:
            arquivo_escolhido = arquivos_vtt[0]

        caminho_vtt = os.path.join(tmpdir, arquivo_escolhido)

        # 6) LEITURA do .vtt com correcao de encoding
        #    yt-dlp pode entregar o VTT com UTF-8 duplamente codificado
        #    (bytes UTF-8 interpretados como latin-1). O _fix_encoding() desfaz isso.
        try:
            with open(caminho_vtt, "rb") as f:
                raw_bytes = f.read()
        except Exception as e:
            return {"status": "erro", "result": f"Falha ao ler o .vtt: {e}"}

        # Tenta UTF-8 estrito primeiro
        try:
            conteudo = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Cai pra latin-1 + _fix_encoding
            conteudo = raw_bytes.decode("latin-1", errors="ignore")
            conteudo = _fix_encoding(conteudo)

        # Alguns VTTs vem com UTF-8 duplamente codificado ("Ã©" no lugar de "é").
        # Aplica _fix_encoding quando detectar o padrao classico.
        if "Ã" in conteudo or "Â" in conteudo:
            conteudo_fixed = _fix_encoding(conteudo)
            # So aceita a correcao se ela realmente reduzir os "Ã"
            if conteudo_fixed.count("Ã") < conteudo.count("Ã"):
                conteudo = conteudo_fixed

        # 7) LIMPEZA do VTT (timecodes, tags, duplicatas)
        linhas = conteudo.split("\n")
        texto_final = []
        for linha in linhas:
            linha_strip = linha.strip()
            if not linha_strip:
                continue
            if linha_strip.startswith("WEBVTT"):
                continue
            if "-->" in linha_strip:
                continue
            if linha_strip.startswith("Kind:"):
                continue
            if linha_strip.startswith("Language:"):
                continue
            linha_limpa = _re.sub(r"<[^>]+>", "", linha_strip).strip()
            if linha_limpa:
                texto_final.append(linha_limpa)

        # Remove linhas duplicadas consecutivas (comum em auto-caption)
        texto_unico = []
        anterior = None
        for linha in texto_final:
            if linha != anterior:
                texto_unico.append(linha)
                anterior = linha

        full_text = "\n".join(texto_unico)

        if not full_text.strip():
            return {
                "status": "erro",
                "result": f"A legenda [{idioma_escolhido}] foi baixada mas esta vazia.",
            }

        return {
            "status": "ok",
            "video_id": video_id,
            "idioma": idioma_escolhido,
            "source": source,  # "manual" ou "auto"
            "full_text": full_text,
            "total_caracteres": len(full_text),
        }


@app.post("/youtube_transcript")
def youtube_transcript(data: YouTubeTranscript):
    print(f"[YOUTUBE_TRANSCRIPT] url={data.url} (via yt-dlp Python API)")
    try:
        resultado = _yt_download_transcript(data.url, data.idiomas)

        if resultado.get("status") != "ok":
            return {"status": "erro", "result": resultado.get("result", "Erro desconhecido")}

        full_text = resultado["full_text"]
        total_chars = resultado["total_caracteres"]

        if total_chars > 5000:
            full_text = full_text[:5000] + f"\n\n... [truncado em 5000 de {total_chars} caracteres]"

        print(f"[YOUTUBE_TRANSCRIPT] OK: idioma={resultado['idioma']} ({resultado['source']}), {total_chars} chars")

        return {
            "status": "ok",
            "result": full_text,
            "video_id": resultado["video_id"],
            "idioma": resultado["idioma"],
            "source": resultado["source"],
            "total_caracteres": total_chars,
        }
    except Exception as e:
        print(f"[YOUTUBE_TRANSCRIPT] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/youtube_summarize")
def youtube_summarize(data: YouTubeSummarize):
    """Baixa transcricao E resume via LLM."""
    print(f"[YOUTUBE_SUMMARIZE] url={data.url}")
    try:
        resultado = _yt_download_transcript(data.url, data.idiomas)

        if resultado.get("status") != "ok":
            return {"status": "erro", "result": resultado.get("result", "Erro desconhecido")}

        full_text = resultado["full_text"]
        video_id = resultado["video_id"]
        idioma = resultado["idioma"]
        source = resultado["source"]

        max_chars = 6000
        texto_para_resumir = full_text[:max_chars] if len(full_text) > max_chars else full_text

        prompt = (
            f"Resuma a transcricao abaixo em no maximo {data.max_pontos} pontos principais. "
            f"Responda em portugues, de forma clara e objetiva. Inclua o tema geral do video.\n\n"
            f"TRANSCRICAO:\n{texto_para_resumir}"
        )

        resumo = _llm_generate(prompt)

        if resumo.get("status") != "ok":
            return {"status": "erro", "result": f"Falha ao resumir: {resumo.get('result')}"}

        texto_resumo = resumo["result"]
        print(f"[YOUTUBE_SUMMARIZE] OK: video={video_id}, resumo {len(texto_resumo)} chars")

        return {
            "status": "ok",
            "result": texto_resumo,
            "video_id": video_id,
            "idioma_transcricao": idioma,
            "source": source,
            "modelo_resumo": resumo.get("modelo_usado", "desconhecido"),
        }
    except Exception as e:
        print(f"[YOUTUBE_SUMMARIZE] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/youtube_ask")
def youtube_ask(data: YouTubeAsk):
    """Baixa a transcricao E responde uma pergunta especifica sobre o video."""
    print(f"[YOUTUBE_ASK] url={data.url} pergunta={data.pergunta[:80]!r}")
    try:
        resultado = _yt_download_transcript(data.url, data.idiomas)

        if resultado.get("status") != "ok":
            return {"status": "erro", "result": resultado.get("result", "Erro desconhecido")}

        full_text = resultado["full_text"]
        video_id = resultado["video_id"]
        idioma = resultado["idioma"]
        source = resultado["source"]

        max_chars = 6000
        texto = full_text[:max_chars] if len(full_text) > max_chars else full_text

        prompt = (
            f"Com base APENAS na transcricao abaixo, responda a seguinte pergunta em portugues:\n\n"
            f"PERGUNTA: {data.pergunta}\n\n"
            f"Se a resposta NAO estiver na transcricao, diga exatamente: "
            f"'Essa informacao nao esta na transcricao do video.'\n\n"
            f"TRANSCRICAO:\n{texto}"
        )

        resposta = _llm_generate(prompt)

        if resposta.get("status") != "ok":
            return {"status": "erro", "result": f"Falha ao processar: {resposta.get('result')}"}

        texto_resposta = resposta["result"]
        print(f"[YOUTUBE_ASK] OK: video={video_id}, resposta {len(texto_resposta)} chars")

        return {
            "status": "ok",
            "result": texto_resposta,
            "video_id": video_id,
            "idioma_transcricao": idioma,
            "source": source,
            "modelo": resposta.get("modelo_usado", "desconhecido"),
        }
    except Exception as e:
        print(f"[YOUTUBE_ASK] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/youtube_save")
def youtube_save(data: YouTubeSave):
    """Baixa a transcricao E salva em workspace/youtube/."""
    print(f"[YOUTUBE_SAVE] url={data.url}")
    try:
        resultado = _yt_download_transcript(data.url, data.idiomas)

        if resultado.get("status") != "ok":
            return {"status": "erro", "result": resultado.get("result", "Erro desconhecido")}

        video_id = resultado["video_id"]
        idioma = resultado["idioma"]
        source = resultado["source"]
        full_text = resultado["full_text"]

        os.makedirs(YOUTUBE_WORKSPACE, exist_ok=True)

        nome_arquivo = data.nome.strip() if data.nome.strip() else video_id
        nome_arquivo = _re.sub(r"[^\w\-.]", "_", nome_arquivo)
        if not nome_arquivo.endswith(".txt"):
            nome_arquivo += ".txt"

        caminho = os.path.join(YOUTUBE_WORKSPACE, nome_arquivo)
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(caminho, "w", encoding="utf-8-sig") as f:
            f.write(f"# Transcricao do video: {video_id}\n")
            f.write(f"# URL original: {data.url}\n")
            f.write(f"# Idioma: {idioma} ({source})\n")
            f.write(f"# Salvo em: {agora}\n")
            f.write(f"# Total de caracteres: {len(full_text)}\n\n")
            f.write(full_text)

        tamanho = os.path.getsize(caminho)
        print(f"[YOUTUBE_SAVE] OK: {caminho} ({tamanho} bytes)")

        return {
            "status": "ok",
            "result": f"Transcricao salva em {nome_arquivo} ({tamanho} bytes, idioma {idioma})",
            "arquivo": nome_arquivo,
            "video_id": video_id,
            "idioma": idioma,
            "source": source,
        }
    except Exception as e:
        print(f"[YOUTUBE_SAVE] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/youtube_list")
def youtube_list(data: YouTubeList):
    """Lista todas as transcricoes salvas em workspace/youtube/."""
    print("[YOUTUBE_LIST]")
    try:
        os.makedirs(YOUTUBE_WORKSPACE, exist_ok=True)
        arquivos = [f for f in os.listdir(YOUTUBE_WORKSPACE) if f.endswith(".txt")]

        if not arquivos:
            return {"status": "ok", "result": "(nenhuma transcricao salva ainda)"}

        linhas = []
        for arq in sorted(arquivos):
            caminho = os.path.join(YOUTUBE_WORKSPACE, arq)
            tamanho = os.path.getsize(caminho)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%d/%m/%Y %H:%M")
            linhas.append(f"{arq} ({tamanho} bytes, salvo em {mtime})")

        resultado = f"{len(arquivos)} transcricao(oes) salva(s):\n" + "\n".join(linhas)
        print(f"[YOUTUBE_LIST] OK: {len(arquivos)} arquivos")
        return {"status": "ok", "result": resultado}
    except Exception as e:
        print(f"[YOUTUBE_LIST] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/youtube_read")
def youtube_read(data: YouTubeRead):
    """Le uma transcricao salva em workspace/youtube/ pelo video_id."""
    print(f"[YOUTUBE_READ] video_id={data.video_id}")
    try:
        os.makedirs(YOUTUBE_WORKSPACE, exist_ok=True)

        candidatos = [data.video_id, data.video_id + ".txt"]

        caminho = None
        for c in candidatos:
            p = os.path.join(YOUTUBE_WORKSPACE, c)
            if os.path.exists(p):
                caminho = p
                break

        if caminho is None:
            return {
                "status": "erro",
                "result": f"Transcricao nao encontrada: {data.video_id}. Use youtube_list para ver as disponiveis.",
            }

        with open(caminho, "r", encoding="utf-8-sig") as f:
            conteudo = f.read()

        if len(conteudo) > data.max_chars:
            conteudo = conteudo[:data.max_chars] + f"\n\n... [truncado em {data.max_chars} de {len(conteudo)} chars]"

        print(f"[YOUTUBE_READ] OK: {caminho}")

        return {
            "status": "ok",
            "result": conteudo,
            "arquivo": os.path.basename(caminho),
        }
    except Exception as e:
        print(f"[YOUTUBE_READ] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


# ============================================================
# FASE 22-light — Task simples com planner + retry
# ============================================================

def _t_search_google(query: str):
    return search_google(SearchGoogle(query=query))

def _t_open_url(url: str):
    return open_url(OpenURL(url=url))

def _t_read_page():
    return read_page()

def _t_web_search(query: str, max_resultados: int = 5):
    return web_search(WebSearch(query=query, max_resultados=max_resultados))

def _t_get_weather(cidade: str = ""):
    return get_weather(GetWeather(cidade=cidade))

def _t_get_current_time():
    return get_current_time()

def _t_youtube_transcript(url: str, idiomas: list = None):
    if idiomas is None:
        idiomas = ["pt", "en"]
    return youtube_transcript(YouTubeTranscript(url=url, idiomas=idiomas))

def _t_responder(pergunta: str):
    resposta = _llm_generate(pergunta)
    if resposta.get("status") == "ok":
        return {"status": "ok", "result": resposta["result"]}
    return resposta

registrar_ferramenta(
    "search_google", _t_search_google,
    "pesquisa no Google (evite; prefira web_search)"
)
registrar_ferramenta(
    "open_url", _t_open_url,
    "abre uma URL especifica no navegador"
)
registrar_ferramenta(
    "read_page", _t_read_page,
    "le o conteudo da pagina atual do navegador"
)
registrar_ferramenta(
    "web_search", _t_web_search,
    "pesquisa na web via DuckDuckGo (use para informacoes gerais, noticias, sites)"
)
registrar_ferramenta(
    "get_weather", _t_get_weather,
    "clima/tempo de uma cidade (use SEMPRE que falar de tempo, temperatura, chuva, previsao)"
)
registrar_ferramenta(
    "get_current_time", _t_get_current_time,
    "hora/data atual (use SEMPRE que falar de horas, datas, dia da semana)"
)
registrar_ferramenta(
    "youtube_transcript", _t_youtube_transcript,
    "transcricao de video do YouTube (use SEMPRE que tiver URL de youtube.com ou youtu.be)"
)
registrar_ferramenta(
    "responder", _t_responder,
    "sintetiza a resposta final em portugues (use como ULTIMO passo sempre)"
)


@app.post("/task_simple")
def task_simple(data: TaskSimple):
    """Executa uma task simples: planeja -> executa -> sintetiza."""
    print(f"[TASK_SIMPLE] objetivo={data.objetivo!r} max_passos={data.max_passos}")
    try:
        resultado = executar_task(data.objetivo, max_passos=data.max_passos)
        return resultado
    except Exception as e:
        print(f"[TASK_SIMPLE] ERRO: {e}")
        return {
            "status": "erro",
            "objetivo": data.objetivo,
            "plano": [],
            "historico": [],
            "resultado_final": None,
            "erro": f"{type(e).__name__}: {e}",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)