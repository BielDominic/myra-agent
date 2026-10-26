import asyncio
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright
import os
import sys
from pathlib import Path
import imaplib
import smtplib
import subprocess
import tempfile
import datetime
import time
import threading
from tasks.cancel_state import marcar_cancelada, marcar_pausada, resetar, resetar_pausa
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import re
import re as _re
import yt_dlp
from tasks.simple_task import executar_task, registrar_ferramenta
from tasks import structured_tools as st
from tasks import browser_bridge as browser_bridge
from tasks import rea_tools as rea_tools
from tasks import remote_access as remote_access
from tasks.telegram_bot import criar_bot_do_ambiente
from tasks.remote_api_auth import validar_token_remoto
from email.message import EmailMessage
from email.header import decode_header
import email as email_lib

# A consola do Windows costuma usar cp1252: um print com emoji (ex.: um nome de
# ficheiro vindo do planner/utilizador) levantava UnicodeEncodeError e derrubava
# a rota com HTTP 500. Forca UTF-8 com substituicao para nunca falhar por print.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

@asynccontextmanager
async def _lifespan(app: FastAPI):
    _telegram_startup()
    try:
        yield
    finally:
        _telegram_shutdown()


app = FastAPI(lifespan=_lifespan)
telegram_bot = criar_bot_do_ambiente()
app.include_router(browser_bridge.router)

# CORS ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â permite o widget (pywebview) acessar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

browser = None
context = None
page = None
playwright = None

PERFIL_DIR = r"C:\computer-agent\chrome_profile"
NOTES_FILE = r"C:\computer-agent\notes.txt"
WORKSPACE_DIR = r"C:\computer-agent\workspace"


def caminho_no_workspace(caminho: str, base: str | None = None) -> str:
    """Resolve um caminho dentro da base e rejeita escapes, incluindo symlinks.

    O commonpath sozinho evita prefixos irmãos, mas não impede que um symlink
    dentro do workspace aponte para fora dele. Path.resolve(strict=False)
    normaliza componentes existentes e inexistentes antes da comparação.
    """
    raiz = Path(base or WORKSPACE_DIR).expanduser().resolve(strict=False)
    destino = (raiz / (caminho or "")).resolve(strict=False)
    try:
        destino.relative_to(raiz)
    except ValueError:
        raise ValueError(f"caminho fora do workspace: {caminho!r}") from None
    return str(destino)


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

# ============================================================
# WIDGET ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Sistema de status em tempo real
# ============================================================

_widget_status = {
    "state": "idle",           # idle | running | done | error | question
    "computer_activity": False,
    "task_id": None,
    "objetivo": None,
    "passo_atual": None,
    "passo_num": 0,
    "passo_total": 0,
    "iniciado_em": None,
    "terminado_em": None,
    "resultado": None,
    "erro": None,
    "historico": [],
}

_widget_listeners = []

# FASE 26 - executor serializado das tasks (uma task por vez). Usado pelas
# rotas que rodam em background, como /task_resume.
_task_pool = None


def _get_task_pool():
    global _task_pool
    if _task_pool is None:
        import concurrent.futures
        _task_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="myra-task"
        )
    return _task_pool


def _widget_notify():
    """Publica imediatamente o snapshot atual para cada listener SSE."""
    snapshot = dict(_widget_status)
    for listener in list(_widget_listeners):
        try:
            loop, event_queue = listener
            if loop.is_closed():
                continue
            # _widget_set tambem pode ser chamado por threads do executor.
            loop.call_soon_threadsafe(event_queue.put_nowait, snapshot)
        except Exception:
            pass


def _widget_set(**kwargs):
    """Atualiza o status do widget e notifica os listeners."""
    global _widget_status
    if kwargs.get("state") in ("idle", "done", "error"):
        kwargs.setdefault("computer_activity", False)
    for k, v in kwargs.items():
        _widget_status[k] = v
    _widget_notify()


class OpenURL(BaseModel):
    url: str


class SearchGoogle(BaseModel):
    query: str


class ClickElement(BaseModel):
    text: str | None = None
    selector: str | None = None


class TypeText(BaseModel):
    selector: str | None = None
    text: str
    field_text: str | None = None


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


class PCOpenApplication(BaseModel):
    nome: str = Field(min_length=1, max_length=160)


class PCUninstallApplication(BaseModel):
    nome: str = Field(min_length=1, max_length=160)


class PCListControls(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    limite: int = Field(default=100, ge=1, le=200)


class PCActuateControl(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    alvo: str = Field(min_length=1, max_length=300)
    acao: str = Field(min_length=1, max_length=30)
    texto: str = Field(default="", max_length=10000)


class PCWindowAction(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    acao: str = Field(min_length=1, max_length=20)


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
    max_passos: int = 15

class RemoteTaskRequest(BaseModel):
    objetivo: str = Field(min_length=1, max_length=1200)
    max_passos: int = Field(default=30, ge=1, le=50)


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
    """Corrige encoding bagunÃƒÆ’Ã‚Â§ado (UTF-8 interpretado como Latin-1)."""
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
    print("[READ_PAGE] tentando Browser Bridge")
    try:
        bridge_result = browser_bridge._browser_read_active_tab_for_route()
        if bridge_result.get("status") == "ok":
            payload = bridge_result.get("result")
            if isinstance(payload, dict):
                texto = str(payload.get("text") or "")[:2000]
                clicaveis = []
                vistos = set()
                for link in payload.get("links", [])[:30]:
                    txt = str(link.get("text") or "").strip()
                    href = str(link.get("href") or "").strip()
                    if txt and txt not in vistos:
                        vistos.add(txt)
                        clicaveis.append(f"LINK {txt} -> {href}")
                for txt in payload.get("buttons", [])[:20]:
                    txt = str(txt or "").strip()
                    if txt and txt not in vistos:
                        vistos.add(txt)
                        clicaveis.append(f"BOTAO {txt}")
                for item in payload.get("inputs", [])[:15]:
                    ph = str(item.get("placeholder") or "")
                    nome = str(item.get("name") or "")
                    tipo = str(item.get("type") or "text")
                    if ph or nome:
                        info = f"CAMPO placeholder={ph} name={nome} type={tipo}"
                        if info not in vistos:
                            vistos.add(info)
                            clicaveis.append(info)
                for tabela in payload.get("tables", [])[:3]:
                    for linha in tabela.get("rows", [])[:10]:
                        info = " | ".join(str(c) for c in linha if c)
                        if info and info not in vistos:
                            vistos.add(info)
                            clicaveis.append(f"TABELA {info}")
                return {
                    "status": "ok",
                    "result": texto,
                    "clicaveis": clicaveis,
                    "title": payload.get("title", ""),
                    "url": payload.get("url", ""),
                    "source": "browser_bridge",
                }
        print(f"[READ_PAGE] bridge indisponivel; fallback Playwright: {bridge_result.get('result', 'sem detalhes')}")
    except Exception as exc:
        print(f"[READ_PAGE] erro no bridge; fallback Playwright: {type(exc).__name__}: {exc}")

    start_browser()
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
    return {"status": "ok", "result": texto, "clicaveis": clicaveis, "source": "playwright"}


# ============================================================
# WIDGET ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Rotas do status em tempo real
# ============================================================

@app.get("/task_status")
def task_status():
    """
    Retorna o status atual da task (pro widget).
    Sem auto-reset: o widget decide quando voltar pra idle.
    """
    return _widget_status


@app.post("/task_cancel")
def task_cancel():
    from tasks.cancel_state import marcar_cancelada
    marcar_cancelada()
    resetar_pausa()  # cancelar tambem limpa uma pausa pendente
    print("[CANCEL] flag de cancelamento setada")

    """
    Cancela a task em execuÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o OU volta pra idle se jÃƒÆ’Ã‚Â¡ terminou.
    Chamado quando o usuÃƒÆ’Ã‚Â¡rio clica em OK, X ou Cancelar.
    """
    global _widget_status

    # Reseta SEMPRE (mesmo se estiver em done/error) ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â permite fechar o card
    _widget_set(
        state="idle",
        task_id=None,
        objetivo=None,
        passo_atual=None,
        passo_num=0,
        passo_total=0,
        iniciado_em=None,
        terminado_em=None,
        resultado=None,
        erro=None,
        historico=[],
    )
    print("[WIDGET] Task resetada pra idle")
    return {"status": "ok", "result": "Task resetada."}


# ============================================================
# FASE 26 - Pausa / retomada de tasks persistidas
# ============================================================

class TaskResumeRequest(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=120)
    max_passos: int | None = None


@app.post("/task_pause")
def task_pause():
    """Pausa a task em execucao.

    O loop para no proximo ponto seguro e o estado (objetivo, passo atual,
    historico, verificacoes e recuperacoes) fica persistido em SQLite, pronto
    para /task_resume continuar sem perder contexto.
    """
    marcar_pausada()
    print("[PAUSE] flag de pausa setada")
    task_id = _widget_status.get("task_id")
    _widget_set(passo_atual="PAUSADO (retome com /task_resume)")
    return {"status": "ok", "result": "Pausa solicitada.", "task_id": task_id}


@app.get("/task_pendentes")
def task_pendentes(limite: int = Query(default=20, ge=0)):
    """Lista tasks pausadas/interrompidas/em execucao que podem ser retomadas."""
    # SQLite LIMIT usa inteiro signed de 64 bits. Valores maiores sao seguros
    # de tratar como o maior limite suportado, sem perder resultados.
    limite = min(limite, 2**63 - 1)
    return {
        "status": "ok",
        "tasks": _simple_task_module.listar_tasks_pendentes(limite=limite),
    }


@app.post("/task_resume")
def task_resume(data: TaskResumeRequest):
    """Retoma uma task persistida (pausa, reinicio do MYRA ou crash).

    Roda em background no executor serializado e atualiza o widget durante a
    execucao. Responda 200 e acompanhe por /task_status ou /task_events.
    """
    try:
        registo = _simple_task_module.task_store.carregar_task(data.task_id)
    except Exception as e:
        return {"status": "erro", "result": f"erro ao carregar task: {e}"}

    if not registo:
        return {"status": "erro", "result": f"task nao encontrada: {data.task_id}"}

    if registo.get("estado") not in _simple_task_module.task_store.ESTADOS_RETOMAVEIS:
        return {
            "status": "erro",
            "result": f"task nao pode ser retomada (estado={registo.get('estado')})",
        }

    resetar()        # limpa cancelamento anterior
    resetar_pausa()  # limpa pausa anterior

    historico_anterior = registo.get("historico") or []
    _widget_set(
        state="running",
        computer_activity=False,
        task_id=data.task_id,
        objetivo=registo.get("objetivo"),
        passo_atual=None,
        passo_num=len(historico_anterior),
        passo_total=registo.get("max_passos") or 15,
        iniciado_em=registo.get("criado_em") or time.time(),
        terminado_em=None,
        resultado=None,
        erro=None,
        historico=[{"ferramenta": h.get("ferramenta")} for h in historico_anterior],
    )

    def _rodar():
        try:
            resultado = _simple_task_module.retomar_task(
                data.task_id, max_passos=data.max_passos
            )
            historico = [
                {"ferramenta": h.get("ferramenta")}
                for h in (resultado.get("historico") or [])
            ]
            status = resultado.get("status")
            if status == "ok":
                _widget_set(
                    state="done",
                    terminado_em=time.time(),
                    resultado=resultado.get("resultado_final"),
                    erro=None,
                    historico=historico,
                )
            elif status == "pausado":
                _widget_set(
                    passo_atual="PAUSADO (retome com /task_resume)",
                    historico=historico,
                )
            elif status == "cancelado":
                _widget_set(state="idle", terminado_em=time.time(), historico=historico)
            else:
                _widget_set(
                    state="error",
                    terminado_em=time.time(),
                    erro=resultado.get("erro") or "falha ao retomar a task",
                    historico=historico,
                )
        except Exception as e:
            print(f"[TASK_RESUME] ERRO: {e}")
            _widget_set(
                state="error", terminado_em=time.time(), erro=f"{type(e).__name__}: {e}"
            )

    _get_task_pool().submit(_rodar)
    return {"status": "ok", "result": "Task retomada.", "task_id": data.task_id}


@app.get("/task_detalhe/{task_id}")
def task_detalhe(task_id: str):
    """Retorna uma task persistida com historico e eventos (auditoria)."""
    try:
        registo = _simple_task_module.task_store.carregar_task(task_id)
        if not registo:
            return {"status": "erro", "result": f"task nao encontrada: {task_id}"}
        registo["eventos"] = _simple_task_module.task_store.listar_eventos(task_id)
        return {"status": "ok", "task": registo}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.get("/task_events")
async def task_events(request: Request):
    """SSE: envia atualizacoes assim que o estado do widget muda."""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json as _json

    async def event_generator():
        loop = asyncio.get_running_loop()
        event_queue = asyncio.Queue()
        listener = (loop, event_queue)
        _widget_listeners.append(listener)
        try:
            yield f"data: {_json.dumps(dict(_widget_status), ensure_ascii=False)}\n\n"
            while not await request.is_disconnected():
                try:
                    snapshot = await asyncio.wait_for(event_queue.get(), timeout=15)
                    yield f"data: {_json.dumps(snapshot, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            try:
                _widget_listeners.remove(listener)
            except ValueError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )




# ============================================================
# VISION LOCATE - acha elementos na tela por descricao textual
# ============================================================

class VisionLocateRequest(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)
    screenshot_path: str | None = None

class VisionTypeRequest(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=200)
    texto: str = Field(..., max_length=5000)
    limpar: bool = True

def _overlay_emit_target(resultado: dict, descricao: str = ""):
    """Publica o alvo no SSE consumido pela janela TARS."""
    if resultado.get("encontrado") and resultado.get("x") is not None and resultado.get("y") is not None:
        x, y = int(resultado["x"]), int(resultado["y"])
        label = str(resultado.get("label") or descricao or "Alvo")[:100]
        _widget_set(target_x=x, target_y=y, target_label=label, overlay={"x": x, "y": y, "label": label})
    else:
        _widget_set(target_x=None, target_y=None, target_label=None, overlay=None)
    return resultado

def _overlay_notify_target(resultado: dict, descricao: str = "") -> bool:
    """Publica o alvo e indica se a task ativa pode aguardar o highlight."""
    _overlay_emit_target(resultado, descricao)
    return _widget_status.get("state") == "running"


@app.post("/vision_locate")
def vision_locate_route(data: VisionLocateRequest):
    """Acha um elemento na tela por descricao textual e publica o alvo no overlay."""
    print(f"[VISION_LOCATE] descricao={data.descricao!r}")
    try:
        from computer import vision_locate as vision_module
        resultado = vision_module.vision_locate(data.descricao, data.screenshot_path)
        return _overlay_emit_target(resultado, data.descricao)
    except Exception as e:
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/vision_click")
def vision_click_route(data: VisionLocateRequest):
    """Localiza, destaca no overlay e clica no centro do elemento."""
    print(f"[VISION_CLICK] descricao={data.descricao!r}")
    try:
        from computer.vision_locate import vision_click
        return vision_click(data.descricao)
    except Exception as e:
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/vision_type")
def vision_type_route(data: VisionTypeRequest):
    """Localiza, destaca, clica e digita no campo."""
    print(f"[VISION_TYPE] descricao={data.descricao!r}")
    try:
        from computer.vision_locate import vision_type
        return vision_type(data.descricao, data.texto, data.limpar)
    except Exception as e:
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


# ============================================================
# FASE 24.2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Rotas auxiliares pras ferramentas estruturadas
# ============================================================

@app.post("/get_current_url")
def get_current_url_route():
    """Retorna a URL atual do navegador controlado."""
    start_browser()
    print("[GET_CURRENT_URL]")
    try:
        url = page.url
        return {"status": "ok", "url": url}
    except Exception as e:
        print(f"[GET_CURRENT_URL] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


@app.post("/read_page_structured")
def read_page_structured_route():
    """Le a pagina e devolve texto, links, botoes, inputs em JSON."""
    start_browser()
    print("[READ_PAGE_STRUCTURED]")
    try:
        url = page.url
        try:
            texto = page.inner_text("body")[:3000]
        except Exception:
            texto = ""

        links = []
        try:
            for a in page.locator("a").all()[:40]:
                try:
                    txt = a.inner_text().strip()[:100]
                    href = a.get_attribute("href") or ""
                    if txt and href:
                        links.append({"texto": txt, "href": href})
                except Exception:
                    pass
        except Exception:
            pass

        botoes = []
        try:
            for b in page.locator("button").all()[:25]:
                try:
                    txt = b.inner_text().strip()[:80]
                    if txt:
                        botoes.append({"texto": txt})
                except Exception:
                    pass
        except Exception:
            pass

        inputs = []
        try:
            for i in page.locator("input, textarea").all()[:20]:
                try:
                    info = {
                        "tipo": i.get_attribute("type") or "text",
                        "name": i.get_attribute("name") or "",
                        "placeholder": i.get_attribute("placeholder") or "",
                    }
                    if info["name"] or info["placeholder"]:
                        inputs.append(info)
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "status": "ok",
            "url": url,
            "texto": texto,
            "links": links,
            "botoes": botoes,
            "inputs": inputs,
            "total_links": len(links),
            "total_botoes": len(botoes),
        }
    except Exception as e:
        print(f"[READ_PAGE_STRUCTURED] ERRO: {e}")
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


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
        # Prioriza o país explicitado para evitar resolver "Roscommon" em outro país.
        nome_busca = cidade
        country_code = ""
        if "irlanda" in cidade.lower() or "ireland" in cidade.lower():
            nome_busca = _re.sub(r"[, ]*(irlanda|ireland)\s*$", "", cidade, flags=_re.IGNORECASE).strip()
            country_code = "&countryCode=IE"
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(nome_busca)}&count=5&language=pt&format=json{country_code}"
        )
        with urllib.request.urlopen(geo_url, timeout=10) as r:
            geo = json.loads(r.read().decode())

        resultados_geo = geo.get("results") or []
        if not resultados_geo:
            return {"status": "erro", "result": f"Cidade '{cidade}' nao encontrada"}

        # Quando o usuário informa um país, escolhe o resultado correspondente.
        local = resultados_geo[0]
        if country_code:
            local = next(
                (item for item in resultados_geo if item.get("country_code") == "IE"),
                local,
            )
        lat = local["latitude"]
        lon = local["longitude"]
        nome = local["name"]
        pais = local.get("country", "")

        clima_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&forecast_days=7&timezone=auto"
        )
        with urllib.request.urlopen(clima_url, timeout=10) as r:
            clima = json.loads(r.read().decode())

        codigos = {
            0: "ceu limpo", 1: "principalmente limpo", 2: "parcialmente nublado", 3: "nublado",
            45: "nevoeiro", 48: "nevoeiro com geada",
            51: "chuvisco leve", 53: "chuvisco moderado", 55: "chuvisco denso",
            56: "chuvisco congelante leve", 57: "chuvisco congelante intenso",
            61: "chuva leve", 63: "chuva moderada", 65: "chuva forte",
            66: "chuva congelante leve", 67: "chuva congelante forte",
            71: "neve leve", 73: "neve moderada", 75: "neve forte", 77: "graos de neve",
            80: "pancadas de chuva leves", 81: "pancadas de chuva moderadas", 82: "pancadas de chuva fortes",
            85: "pancadas de neve leves", 86: "pancadas de neve fortes",
            95: "trovoada", 96: "trovoada com granizo leve", 99: "trovoada com granizo forte",
        }

        atual = clima.get("current") or {}
        descricao_atual = codigos.get(atual.get("weather_code"), "condicao indisponivel")
        resultado = (
            f"Clima atual em {nome}, {pais}: {atual.get('temperature_2m', 'N/D')}°C, "
            f"{descricao_atual}, umidade {atual.get('relative_humidity_2m', 'N/D')}%, "
            f"vento {atual.get('wind_speed_10m', 'N/D')} km/h.\n"
            "Previsao para os proximos 7 dias:"
        )

        diaria = clima.get("daily") or {}
        datas = diaria.get("time") or []
        maximas = diaria.get("temperature_2m_max") or []
        minimas = diaria.get("temperature_2m_min") or []
        codigos_diarios = diaria.get("weather_code") or []
        chuva = diaria.get("precipitation_probability_max") or []
        linhas = []
        for i, data_dia in enumerate(datas[:7]):
            codigo_dia = codigos_diarios[i] if i < len(codigos_diarios) else None
            desc_dia = codigos.get(codigo_dia, "condicao indisponivel")
            minima = minimas[i] if i < len(minimas) else "N/D"
            maxima = maximas[i] if i < len(maximas) else "N/D"
            prob_chuva = chuva[i] if i < len(chuva) and chuva[i] is not None else "N/D"
            linhas.append(
                f"{data_dia}: {desc_dia}; minima {minima}°C, maxima {maxima}°C; "
                f"probabilidade maxima de chuva {prob_chuva}%"
            )
        if not linhas:
            return {"status": "erro", "result": "A fonte meteorologica nao retornou previsao diaria."}
        resultado += "\n" + "\n".join(linhas)
        return {"status": "ok", "result": resultado}
    except Exception as e:
        print(f"[GET_WEATHER] ERRO: {e}")
        return {"status": "erro", "result": f"Erro ao consultar a previsao meteorologica: {type(e).__name__}: {e}"}


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
        try:
            caminho_completo = caminho_no_workspace(data.caminho)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

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
        try:
            caminho_completo = caminho_no_workspace(data.caminho)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

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
        try:
            caminho_completo = caminho_no_workspace(data.caminho)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

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

        # O helper de screenshot pode devolver o caminho como "arquivo" (contrato legado)
        # ou "path" (contrato novo); aceite ambos para não abortar a análise visual.
        arquivo = resultado.get("path") or resultado.get("arquivo")
        if not arquivo or not os.path.exists(arquivo):
            return {"status": "erro", "result": "Screenshot nao foi salvo corretamente"}

        print(f"[SEE] screenshot do PC salvo em {arquivo}")

        import base64 as _base64
        # Capturas desktop grandes tornam a inferência multimodal local excessivamente
        # lenta. Redimensione mantendo a captura original no disco para auditoria.
        try:
            from PIL import Image as _Image
            import io as _io
            with _Image.open(arquivo) as _screen:
                _screen.thumbnail((1024, 768))
                _buffer = _io.BytesIO()
                _screen.convert("RGB").save(_buffer, format="JPEG", quality=78, optimize=True)
                img_b64 = _base64.b64encode(_buffer.getvalue()).decode("ascii")
                img_mime = "image/jpeg"
        except ImportError:
            with open(arquivo, "rb") as f:
                img_b64 = _base64.b64encode(f.read()).decode("ascii")
            img_mime = "image/png"

        payload = {
            "model": "Qwen3.5-0.8B",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": data.pergunta + "\n\nREGRAS OBRIGATORIAS: responda em portugues em 3 frases curtas. Use somente caracteres ASCII (sem acentos) para evitar falhas de codificacao. Descreva apenas o que esta realmente visivel na imagem enviada. Priorize a janela em primeiro plano e os elementos que podem ser lidos; se houver um chat, descreva as mensagens visiveis sem inventar o restante da tela. Nao deduza sistema operacional, horario, identidade, intencoes, contas ou contexto que nao estejam claramente visiveis. Nao repita a pergunta. Nao invente botoes, paineis ou icones. Se nao conseguir ler algo, diga isso. Sem titulo, lista ou markdown; termine cada frase com pontuacao."},
                        {"type": "image_url", "image_url": {"url": f"data:{img_mime};base64,{img_b64}"}}
                    ]
                }
            ],
            "max_tokens": 2000,
        }

        req = urllib.request.Request(
            LLM_EYES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        finish_reason = None
        vision_backend = "openai_compatible"
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                resposta = json.loads(r.read().decode("utf-8"))
            escolha = (resposta.get("choices") or [{}])[0]
            msg = escolha.get("message") or {}
            finish_reason = escolha.get("finish_reason")
            usage = resposta.get("usage") or {}
            conteudo = msg.get("content", "") or msg.get("reasoning_content", "")
            print(
                f"[SEE] finish_reason={finish_reason} "
                f"completion_tokens={usage.get('completion_tokens')} chars={len(conteudo)}"
            )
        except (urllib.error.URLError, TimeoutError, ConnectionError) as vision_error:
            # O servidor OpenAI-compatível dedicado pode estar desligado; use o Ollama
            # local com modelo multimodal como fallback, sem abandonar a análise visual.
            print(f"[SEE] endpoint visual indisponivel ({type(vision_error).__name__}); tentando Ollama multimodal")
            vision_backend = "ollama"
            fallback_payload = {
                "model": "qwen3.5:4b",
                "messages": [{
                    "role": "user",
                    "content": (
                        f"{data.pergunta}\n\nResponda em portugues em 3 frases curtas e use somente caracteres ASCII, sem acentos. "
                        "Descreva apenas o que esta realmente visivel na imagem. Priorize a janela em primeiro plano e o texto legivel. "
                        "Se houver um chat, descreva as mensagens visiveis sem inventar o restante da tela. Nao deduza sistema operacional, horario, identidade ou contexto nao visivel. "
                        "Nao invente botoes, paineis ou icones. Sem titulo, markdown ou lista; termine cada frase com pontuacao."
                    ),
                    "images": [img_b64],
                }],
                "stream": False,
                "think": False,
                "options": {"num_predict": 1200, "temperature": 0.1},
            }
            fallback_req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=json.dumps(fallback_payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(fallback_req, timeout=150) as r:
                fallback_response = json.loads(r.read().decode("utf-8"))
            conteudo = (fallback_response.get("message") or {}).get("content", "")
            finish_reason = fallback_response.get("done_reason")
            print(f"[SEE] backend=ollama done={fallback_response.get('done')} done_reason={finish_reason} eval_count={fallback_response.get('eval_count')} chars={len(conteudo)}")

        # Validar ambos os backends; o fallback Ollama tambem pode truncar a resposta.
        if isinstance(conteudo, str) and conteudo.strip():
            resposta_incompleta = finish_reason == "length" or not re.search(
                r'[.!?…]["”’)]*\s*$',
                conteudo.strip(),
            )
            if resposta_incompleta:
                print(f"[SEE] resposta possivelmente incompleta; tentando regenerar (finish_reason={finish_reason})")
                if vision_backend == "ollama":
                    retry_payload = {
                        "model": "qwen3.5:4b",
                        "messages": [{"role": "user", "content": "Descreva somente a captura em 3 a 5 frases curtas em portugues. Sem titulo, introducao, markdown ou lista. Nao infira identidade, conta, intencao, oferta ou contexto anterior. Nao adivinhe texto ilegivel. Termine com pontuacao.", "images": [img_b64]}],
                        "stream": False,
                        "think": False,
                        "options": {"num_predict": 1200, "temperature": 0.1},
                    }
                else:
                    retry_payload = dict(payload)
                    retry_payload["max_tokens"] = 1200
                    retry_payload["messages"] = [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Descreva somente a captura em 3 a 5 frases curtas em português. Sem título, introdução, markdown ou lista. "
                                "Não infira identidade, conta, intenção, oferta ou contexto anterior. Não adivinhe texto ilegível. "
                                "Termine com pontuação."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:{img_mime};base64,{img_b64}"}},
                    ],
                }]
                retry_url = "http://127.0.0.1:11434/api/chat" if vision_backend == "ollama" else LLM_EYES_URL
                retry_req = urllib.request.Request(
                    retry_url,
                    data=json.dumps(retry_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(retry_req, timeout=150 if vision_backend == "ollama" else 120) as r:
                        retry_response = json.loads(r.read().decode("utf-8"))
                    if vision_backend == "ollama":
                        retry_content = (retry_response.get("message") or {}).get("content", "")
                        retry_reason = retry_response.get("done_reason")
                        retry_stopped = retry_response.get("done") is True and retry_reason != "length"
                    else:
                        retry_choice = (retry_response.get("choices") or [{}])[0]
                        retry_message = retry_choice.get("message") or {}
                        retry_content = retry_message.get("content", "") or retry_message.get("reasoning_content", "")
                        retry_reason = retry_choice.get("finish_reason")
                        retry_stopped = retry_reason != "length"
                    if retry_content and re.search(r'[.!?…]["”’)]*\s*$', retry_content.strip()) and retry_stopped:
                        conteudo = retry_content
                        print(f"[SEE] regeneração concluída: chars={len(conteudo)}")
                    else:
                        print(f"[SEE] regeneração também incompleta (finish_reason={retry_reason})")
                        return {
                            "status": "erro",
                            "result": "A análise visual foi interrompida pelo modelo mesmo após uma nova tentativa. Nenhuma descrição incompleta foi enviada; tente novamente.",
                            "screenshot": arquivo,
                        }
                except Exception as retry_error:
                    print(f"[SEE] falha na regeneração: {type(retry_error).__name__}")
                    return {
                        "status": "erro",
                        "result": "A análise visual foi interrompida e não foi possível concluir a nova tentativa. Nenhuma descrição incompleta foi enviada; tente novamente.",
                        "screenshot": arquivo,
                    }

        if not isinstance(conteudo, str) or not conteudo.strip():
            print("[SEE] ERRO: modelo visual retornou resposta vazia")
            return {"status": "erro", "result": "O modelo visual não retornou uma descrição da tela. A captura foi feita, mas a análise falhou; tente novamente ou verifique o modelo multimodal do Ollama.", "screenshot": arquivo}

        # Defesa determinística: alguns modelos ignoram instruções de formato e devolvem
        # títulos/listas ou contexto especulativo. Normalizar a saída antes de enviá-la.
        linhas = []
        for linha in conteudo.splitlines():
            linha = _re.sub(r"^\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)", "", linha).strip()
            if linha and linha not in ("---", "***", "___"):
                linhas.append(linha)
        conteudo = " ".join(linhas).strip()
        # Limita a descrição a no máximo cinco frases completas; evita relatórios longos.
        frases = _re.split(r"(?<=[.!?…])\s+(?=[A-ZÀ-Þ0-9“\"'])", conteudo)
        frases = [f.strip() for f in frases if f.strip()]
        if len(frases) > 5:
            conteudo = " ".join(frases[:5])
        if len(conteudo) > 1100:
            corte = conteudo[:1100]
            ultimo_fim = max(corte.rfind("."), corte.rfind("!"), corte.rfind("?"), corte.rfind("…"))
            if ultimo_fim > 250:
                conteudo = corte[:ultimo_fim + 1].strip()
        print(f"[SEE] resposta normalizada: {len(conteudo)} chars")
        print(f"[SEE] resposta: {conteudo[:100]}...")
        return {"status": "ok", "result": conteudo, "screenshot": arquivo}
    except Exception as e:
        print(f"[SEE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/delete_file")
def delete_file(data: DeleteFile):
    print(f"[DELETE_FILE] caminho={data.caminho}")
    try:
        try:
            caminho_completo = caminho_no_workspace(data.caminho)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

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
        try:
            caminho_completo = caminho_no_workspace(data.caminho)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

        os.makedirs(caminho_completo, exist_ok=True)
        return {"status": "ok", "result": f"Pasta criada: {data.caminho}"}
    except Exception as e:
        print(f"[CREATE_DIR] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/move_file")
def move_file(data: MoveFile):
    print(f"[MOVE_FILE] origem={data.origem} destino={data.destino}")
    try:
        try:
            origem_completa = caminho_no_workspace(data.origem)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado (origem): {e}"}
        try:
            destino_completo = caminho_no_workspace(data.destino)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado (destino): {e}"}

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
from computer.applications import listar_aplicativos as _pc_listar_aplicativos, abrir_aplicativo as _pc_abrir_aplicativo, desinstalar_aplicativo as _pc_desinstalar_aplicativo
from computer.ui_automation import listar_controles as _pc_listar_controles, acionar_controle as _pc_acionar_controle, gerenciar_janela as _pc_gerenciar_janela
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


@app.post("/pc_list_applications")
def pc_applications():
    """Lista atalhos de aplicativos acessíveis no menu Iniciar e desktops."""
    print("[PC_APPLICATIONS] inventario de atalhos")
    return _pc_listar_aplicativos()


@app.post("/pc_open_application")
def pc_open_application(data: PCOpenApplication):
    """Abre um aplicativo por atalho conhecido, sem executar comandos arbitrarios."""
    print(f"[PC_OPEN_APPLICATION] nome={data.nome}")
    return _pc_abrir_aplicativo(data.nome)


@app.post("/pc_uninstall_application")
def pc_uninstall_application(data: PCUninstallApplication):
    print(f"[PC_UNINSTALL_APPLICATION] nome={data.nome}")
    return _pc_desinstalar_aplicativo(data.nome)


@app.post("/pc_list_controls")
def pc_list_controls(data: PCListControls):
    return _pc_listar_controles(data.titulo, data.limite)


@app.post("/pc_control_action")
def pc_control_action(data: PCActuateControl):
    return _pc_acionar_controle(data.titulo, data.alvo, data.acao, data.texto)


@app.post("/pc_window_action")
def pc_window_action(data: PCWindowAction):
    return _pc_gerenciar_janela(data.titulo, data.acao)


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
        try:
            caminho_completo = caminho_no_workspace(data.caminho, CODE_WORKSPACE)
        except ValueError as e:
            return {"status": "erro", "result": f"Acesso negado: {e}"}

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
# YOUTUBE ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â FASE 20.1: deteccao automatica de idioma via yt-dlp
# ============================================================

YOUTUBE_ID_REGEX = _re.compile(r"(?:v=|youtu\.be/|youtube\.com/embed/|shorts/)([A-Za-z0-9_-]{11})")
YOUTUBE_WORKSPACE = os.path.join(WORKSPACE_DIR, "youtube")

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

    manual = [l for l in manual_raw.keys() if l != "live_chat"]
    auto = [l for l in auto_raw.keys() if l != "live_chat"]

    return {"ok": True, "manual": manual, "auto": auto, "error": None}


def _yt_escolher_idioma(disponiveis_manual: list, disponiveis_auto: list, preferidos: list):
    for lang in preferidos:
        for m in disponiveis_manual:
            if m == lang or m.startswith(lang + "-"):
                return m, "manual"
        for a in disponiveis_auto:
            if a == lang or a.startswith(lang + "-"):
                return a, "auto"

    if disponiveis_manual:
        return disponiveis_manual[0], "manual"
    if disponiveis_auto:
        return disponiveis_auto[0], "auto"

    return None, None


def _yt_download_transcript(url: str, idiomas: list = None) -> dict:
    video_id = _yt_extract_video_id(url)

    if idiomas:
        preferidos = list(idiomas)
        for l in YOUTUBE_LANGS_PADRAO:
            if l not in preferidos:
                preferidos.append(l)
    else:
        preferidos = list(YOUTUBE_LANGS_PADRAO)

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

    idioma_escolhido, source = _yt_escolher_idioma(manual, auto, preferidos)
    if not idioma_escolhido:
        return {
            "status": "erro",
            "result": "Nenhuma legenda utilizavel encontrada para este video.",
        }

    print(f"[YT] video={video_id} manual={manual} auto={auto} escolhido={idioma_escolhido} ({source})")

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

        arquivos_vtt = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not arquivos_vtt:
            return {
                "status": "erro",
                "result": (
                    f"Baixou mas nao achou .vtt (idioma {idioma_escolhido}). "
                    "Talvez o YouTube tenha retornado vazio (429?)."
                ),
            }

        arquivo_escolhido = None
        for arq in arquivos_vtt:
            if f".{idioma_escolhido}." in arq:
                arquivo_escolhido = arq
                break
        if not arquivo_escolhido:
            arquivo_escolhido = arquivos_vtt[0]

        caminho_vtt = os.path.join(tmpdir, arquivo_escolhido)

        try:
            with open(caminho_vtt, "rb") as f:
                raw_bytes = f.read()
        except Exception as e:
            return {"status": "erro", "result": f"Falha ao ler o .vtt: {e}"}

        try:
            conteudo = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            conteudo = raw_bytes.decode("latin-1", errors="ignore")
            conteudo = _fix_encoding(conteudo)

        if "ÃƒÆ’Ã†â€™" in conteudo or "ÃƒÆ’Ã¢â‚¬Å¡" in conteudo:
            conteudo_fixed = _fix_encoding(conteudo)
            if conteudo_fixed.count("ÃƒÆ’Ã†â€™") < conteudo.count("ÃƒÆ’Ã†â€™"):
                conteudo = conteudo_fixed

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
            "source": source,
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
# FASE 22-light ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Task simples com planner + retry
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

# FASE 24.2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Ferramentas estruturadas (devolvem JSON)
st.registrar_todas(registrar_ferramenta)
browser_bridge.registrar_ferramentas(registrar_ferramenta)

# Mantém os 12 nomes de ferramentas de navegador já publicados, mas liga-os
# ao Playwright isolado do agent.py. A extensão/Browser Bridge continua com suas
# rotas próprias, porém o planner não controla a sessão real do Chrome.
# Helpers internos de Playwright. Não são entradas extras no registro:
# os nomes públicos browser_* permanecem exatamente os mesmos.
def _t_playwright_open_url(url: str):
    try:
        return _t_open_url(url)
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright open_url: {type(exc).__name__}: {exc}"}

def _t_playwright_search_google(query: str):
    try:
        return _t_search_google(query)
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright search_google: {type(exc).__name__}: {exc}"}

def _t_playwright_search_in_page(query: str):
    try:
        return search_in_page(SearchGoogle(query=query))
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright search_in_page: {type(exc).__name__}: {exc}"}

def _t_playwright_click_element(text: str = "", selector: str = ""):
    try:
        return click_element(ClickElement(text=text or None, selector=selector or None))
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright click: {type(exc).__name__}: {exc}"}

def _t_playwright_type_text(text: str, field_text: str = "", selector: str = ""):
    try:
        return type_text(TypeText(text=text, field_text=field_text or None, selector=selector or None))
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright type_text: {type(exc).__name__}: {exc}"}

def _t_playwright_press_key(key: str):
    try:
        return press_key(PressKey(key=key))
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright press_key: {type(exc).__name__}: {exc}"}

def _t_playwright_go_back():
    try:
        return go_back()
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright go_back: {type(exc).__name__}: {exc}"}

def _t_playwright_wait(seconds: float = 1):
    """Espera sem abrir/recriar o perfil persistente do navegador."""
    try:
        segundos = max(0.0, min(float(seconds), 30.0))
        time.sleep(segundos)
        return {"status": "ok", "result": f"Esperei {segundos:g}s"}
    except Exception as exc:
        return {"status": "erro", "result": f"Browser wait: {type(exc).__name__}: {exc}"}

def _t_playwright_read_page():
    try:
        start_browser()
        titulo = page.title()
        url = page.url
        texto = page.locator("body").inner_text(timeout=10000)[:5000]
        links = page.locator("a").evaluate_all(
            "(els) => els.slice(0, 25).map(a => ({text: (a.innerText || '').trim(), href: a.href}))"
        )
        linhas = [f"Title: {titulo}", f"URL: {url}", f"Texto visivel:\n{texto}"]
        linhas.extend(f"LINK {x.get('text', '')} -> {x.get('href', '')}" for x in links if x.get("text"))
        return {"status": "ok", "result": "\n".join(linhas), "title": titulo, "url": url, "text": texto, "links": links}
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright read_page: {type(exc).__name__}: {exc}"}

def _t_playwright_scroll(direcao: str = "down", quantidade: int = 500):
    try:
        start_browser()
        if direcao == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif direcao == "bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            page.mouse.wheel(0, -abs(quantidade) if direcao == "up" else abs(quantidade))
        page.wait_for_timeout(300)
        return {"status": "ok", "result": f"Scroll {direcao} executado em {page.url}"}
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright scroll: {type(exc).__name__}: {exc}"}

def _t_browser_get_tabs():
    try:
        start_browser()
        tabs = []
        for idx, tab in enumerate(context.pages):
            try:
                tabs.append({"id": idx, "title": tab.title(), "url": tab.url, "active": tab is page})
            except Exception:
                continue
        return {"status": "ok", "result": tabs, "tabs": tabs}
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright get_tabs: {type(exc).__name__}: {exc}"}

def _t_browser_read_active_tab(url_contains: str = ""):
    try:
        start_browser()
        if url_contains and url_contains.lower() not in page.url.lower():
            return {"status": "erro", "result": f"A página Playwright atual ({page.url}) não corresponde a {url_contains!r}."}
        return _t_playwright_read_page()
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright read_active_tab: {type(exc).__name__}: {exc}"}

def _t_browser_read_page(url: str = ""):
    try:
        start_browser()
        if url:
            page.goto(url, timeout=15000)
        return _t_playwright_read_page()
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright read_page: {type(exc).__name__}: {exc}"}

def _t_browser_navigate_active_tab(url: str):
    return _t_playwright_open_url(url)

def _t_browser_new_tab(url: str):
    global page
    try:
        start_browser()
        page = context.new_page()
        page.goto(url, timeout=15000)
        return {"status": "ok", "result": f"Abri {url} em uma nova página Playwright.", "url": page.url, "title": page.title()}
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright new_tab: {type(exc).__name__}: {exc}"}

def _t_browser_close_tab(tab_id: int = None):
    global page
    try:
        start_browser()
        pages = list(context.pages)
        if not pages:
            page = context.new_page()
            return {"status": "ok", "result": "Criei uma nova página Playwright."}
        idx = tab_id if isinstance(tab_id, int) and not isinstance(tab_id, bool) else len(pages) - 1
        if idx < 0 or idx >= len(pages):
            return {"status": "erro", "result": f"ID de página Playwright inválido: {tab_id}"}
        pages[idx].close()
        remaining = list(context.pages)
        page = remaining[-1] if remaining else context.new_page()
        return {"status": "ok", "result": "Página Playwright fechada.", "url": page.url}
    except Exception as exc:
        return {"status": "erro", "result": f"Playwright close_tab: {type(exc).__name__}: {exc}"}

def _t_browser_type_text(campo: str, texto: str):
    return _t_playwright_type_text(text=texto, field_text=campo)

def _t_browser_click_text(
    text: str = "", descricao: str = "", selector: str = "",
    campo: str = "", texto: str = "",
):
    # O planner pode emitir nomes de argumentos em PT-BR (descricao/campo/texto)
    # mesmo quando seleciona a ferramenta de clique. Normalize-os sem TypeError.
    alvo = text or descricao or campo or texto
    return _t_playwright_click_element(text=alvo, selector=selector)

def _t_browser_scroll(direcao: str = "down", quantidade: int = 500):
    return _t_playwright_scroll(direcao=direcao, quantidade=quantidade)

def _t_browser_search_google(termo: str):
    return _t_playwright_search_google(query=termo)

def _t_browser_search_google_visivel(termo: str, delay_typing_ms: int = 150, scroll_suave: bool = False):
    return _t_playwright_search_google(query=termo)

def _t_browser_wait(ms: int = 1000):
    return _t_playwright_wait(seconds=max(0, min(int(ms), 30000)) / 1000)

for _name, _fn, _description in (
    ("browser_get_tabs", _t_browser_get_tabs, "Lista páginas do navegador Playwright isolado da MYRA; não acessa abas reais do Chrome."),
    ("browser_read_active_tab", _t_browser_read_active_tab, "Lê a página atual do Playwright isolado. Opcional: url_contains para validar a URL atual."),
    ("browser_read_page", _t_browser_read_page, "Lê título, URL, texto e links usando Playwright; opcionalmente navega para url antes de ler."),
    ("browser_navigate_active_tab", _t_browser_navigate_active_tab, "Navega a página Playwright atual para uma URL HTTP/HTTPS."),
    ("browser_new_tab", _t_browser_new_tab, "Abre URL numa nova página Playwright isolada da MYRA; não usa a sessão real do Chrome."),
    ("browser_close_tab", _t_browser_close_tab, "Fecha uma página Playwright por índice opcional tab_id; cria uma página em branco se necessário."),
    ("browser_type_text", _t_browser_type_text, "Preenche um campo da página Playwright; campos: campo e texto."),
    ("browser_click_text", _t_browser_click_text, "Clica por texto visível na página Playwright."),
    ("browser_scroll", _t_browser_scroll, "Rola a página Playwright; direcao up/down/top/bottom e quantidade em pixels."),
    ("browser_search_google_visivel", _t_browser_search_google_visivel, "Pesquisa no Google com Playwright local e mantém a página aberta; não usa extensão Chrome."),
    ("browser_search_google", _t_browser_search_google, "Pesquisa no Google com Playwright local e retorna resultado."),
    ("browser_wait", _t_browser_wait, "Aguarda milissegundos sem bloquear o Chrome real; usa a página Playwright local."),
):
    registrar_ferramenta(_name, _fn, _description)

# Ferramentas de sistema (arquivos, codigo, email, PC, utilitarias)
import tasks.system_tools as _system_tools
_system_tools.registrar_todas(registrar_ferramenta)

# FASE 27.5 - analise REA opcional, local e restrita a raizes autorizadas.
rea_tools.registrar_todas(registrar_ferramenta)

# ============================================================
# VISION LOCATE - ferramentas do planner
# ============================================================
from computer import vision_locate as _vision_module
from computer.vision_locate import vision_locate as _vision_locate_fn
from computer.vision_locate import vision_click as _vision_click_fn
from computer.vision_locate import vision_type as _vision_type_fn

# Injetar callback antes de registrar as ferramentas para destacar o alvo antes
# de o modulo vision_locate clicar ou digitar.
_vision_module.OVERLAY_TARGET_CALLBACK = _overlay_notify_target


def _t_vision_locate(descricao: str):
    return _overlay_emit_target(_vision_locate_fn(descricao), descricao)


def _t_vision_click(descricao: str):
    return _vision_click_fn(descricao)


def _t_vision_type(descricao: str, texto: str, limpar: bool = True):
    return _vision_type_fn(descricao, texto, limpar)

registrar_ferramenta(
    "vision_locate", _t_vision_locate,
    "Acha um elemento na tela pela descricao textual. Retorna coordenadas x, y. Use quando precisar saber onde clicar em algo que voce ve na tela mas nao sabe a posicao. Obrigatorio: descricao (ex: 'botao de login', 'New Chat')."
)
registrar_ferramenta(
    "vision_click", _t_vision_click,
    "Acha um elemento pela descricao e clica no centro dele. Use quando quiser clicar em algo visivel sem saber as coordenadas. Obrigatorio: descricao."
)
registrar_ferramenta(
    "vision_type", _t_vision_type,
    "Acha um campo pela descricao, clica e digita texto. Use para preencher formularios visualmente. Obrigatorio: descricao e texto."
)

# ============================================================
# VISION LOCATE - ferramentas do planner
# ============================================================



# FASE 24.4 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Injeta _widget_set no simple_task (evita import circular)
import tasks.simple_task as _simple_task_module
_simple_task_module._widget_set_injetado = _widget_set

# FASE 26 - no startup, tasks que ficaram "em_execucao" de um processo anterior
# (crash, fecho forcado, reinicio) viram "interrompido" e podem ser retomadas
# por /task_resume sem perder o historico.
try:
    _interrompidas = _simple_task_module.task_store.marcar_interrompidas()
    if _interrompidas:
        print(f"[STORE] {_interrompidas} task(s) marcada(s) como interrompida(s) - use /task_resume")
except Exception as _e:
    print(f"[STORE] aviso: nao foi possivel marcar tasks interrompidas: {_e}")


def _task_simple_impl(data: TaskSimple):
    """Executa uma task simples dentro do executor serializado da MYRA."""
    print(f"[TASK_SIMPLE] objetivo={data.objetivo!r} max_passos={data.max_passos}")

    resetar()        # limpa cancelamento anterior
    resetar_pausa()  # limpa pausa anterior

    # Atualiza o widget: task comeÃƒÆ’Ã‚Â§ou
    _widget_set(
        state="running",
        computer_activity=False,
        task_id=str(int(time.time())),
        objetivo=data.objetivo,
        passo_atual=None,
        passo_num=0,
        passo_total=0,
        iniciado_em=time.time(),
        terminado_em=None,
        resultado=None,
        erro=None,
        historico=[],
    )

    try:
        resultado = executar_task(data.objetivo, max_passos=data.max_passos)

        # Atualiza o widget: task terminou
        if resultado.get("status") == "ok":
            _widget_set(
                state="done",
                terminado_em=time.time(),
                resultado=resultado.get("resultado_final"),
                erro=None,
                historico=[
                    {"ferramenta": p.get("ferramenta"), "args": p.get("args")}
                    for p in resultado.get("plano", [])
                ],
            )
        elif resultado.get("status") == "pausado":
            # FASE 26 - task pausada: estado persistido, retomavel por /task_resume
            _widget_set(
                state="running",
                passo_atual="PAUSADO (retome com /task_resume)",
                historico=[
                    {"ferramenta": h.get("ferramenta"), "args": h.get("args")}
                    for h in resultado.get("historico", [])
                ],
            )
        else:
            _widget_set(
                state="error",
                terminado_em=time.time(),
                resultado=None,
                erro=resultado.get("erro") or resultado.get("result"),
            )

        return resultado
    except Exception as e:
        print(f"[TASK_SIMPLE] ERRO: {e}")
        _widget_set(
            state="error",
            terminado_em=time.time(),
            erro=f"{type(e).__name__}: {e}",
        )
        return {
            "status": "erro",
            "objetivo": data.objetivo,
            "plano": [],
            "historico": [],
            "resultado_final": None,
            "erro": f"{type(e).__name__}: {e}",
        }


@app.post("/task_simple")
def task_simple(data: TaskSimple):
    """Executa tasks no mesmo thread serializado usado pela retomada.

    O Playwright Sync API exige afinidade de thread. Sem serializar a task
    inicial e a retomada no mesmo executor, um contexto global do navegador
    criado por uma thread podia ser reutilizado por outra e falhar com
    "Sync API inside the asyncio loop" / "Cannot switch to a different thread".
    """
    return _get_task_pool().submit(_task_simple_impl, data).result()


# ============================================================
# FASE 28.3 - API remota autenticada para clientes mobile
# ============================================================
_remote_task_lock = threading.Lock()
_remote_task_scheduled = False

def _require_remote_api(authorization: str | None = Header(default=None)):
    return validar_token_remoto(authorization)

def _run_remote_task(data: TaskSimple):
    global _remote_task_scheduled
    try:
        task_simple(data)
    finally:
        with _remote_task_lock:
            _remote_task_scheduled = False

@app.get("/remote/v1/status")
def remote_v1_status(_authorized: bool = Depends(_require_remote_api)):
    status = _widget_status if isinstance(_widget_status, dict) else {}
    return {
        "state": status.get("state", "idle"),
        "task_id": status.get("task_id"),
        "objetivo": status.get("objetivo"),
        "passo_atual": status.get("passo_atual"),
        "passo_num": status.get("passo_num", 0),
        "passo_total": status.get("passo_total", 0),
        "resultado": status.get("resultado"),
        "erro": status.get("erro"),
    }

@app.post("/remote/v1/task")
def remote_v1_start_task(data: RemoteTaskRequest, background_tasks: BackgroundTasks, _authorized: bool = Depends(_require_remote_api)):
    global _remote_task_scheduled
    if not data.objetivo.strip():
        raise HTTPException(status_code=422, detail="Informe um objetivo de tarefa nao vazio.")
    with _remote_task_lock:
        if _remote_task_scheduled or _widget_status.get("state") == "running":
            raise HTTPException(status_code=409, detail="Ja existe uma tarefa em execucao.")
        _remote_task_scheduled = True
        background_tasks.add_task(_run_remote_task, TaskSimple(objetivo=data.objetivo.strip(), max_passos=data.max_passos))
    return {"status": "accepted", "result": "Tarefa recebida pela MYRA."}

@app.post("/remote/v1/cancel")
def remote_v1_cancel(_authorized: bool = Depends(_require_remote_api)):
    return task_cancel()


# ============================================================
# FASE 28.2 - Controle remoto Telegram (opt-in por variaveis de ambiente)
# ============================================================

@app.get("/telegram/status")
def telegram_status():
    return telegram_bot.status()


@app.get("/remote_access/status")
def remote_access_status():
    return remote_access.tailscale_status()


@app.post("/telegram/start")
def telegram_start():
    return telegram_bot.start()


@app.post("/telegram/stop")
def telegram_stop():
    return telegram_bot.stop()


def _telegram_startup():
    # Nunca habilita o bot sem token e chat IDs explicitamente autorizados.
    if telegram_bot.configured:
        resultado = telegram_bot.start()
        print("[TELEGRAM] bot habilitado por configuracao de ambiente" if resultado.get("status") == "ok"
              else "[TELEGRAM] configuracao encontrada, mas o bot nao iniciou")


def _telegram_shutdown():
    telegram_bot.stop()


# ============================================================
# FASE 24.5 - Rota OpenAI-compatible (integracao com Open WebUI)
# ============================================================

from fastapi.responses import JSONResponse


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """Rota OpenAI-compatible. Recebe mensagem do Open WebUI, executa via executar_task, devolve no formato OpenAI."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    data = _myra_apply_identity_headers(data, request.headers)
    messages = data.get("messages", [])
    model = data.get("model", "myra-agent")

    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_msg = part.get("text", "")
                        break
            else:
                user_msg = content
            break

    print(f"[OPENAI] model={model} msg={user_msg!r}")

    # Open WebUI envia prompts auxiliares para título, follow-ups e tags.
    # Eles não são tarefas do usuário e não devem sobrescrever o estado do widget.
    _msg_lower = user_msg.lower()
    _marcadores_internos = [
        "### task:",
        "generate a concise title",
        "generate 1-3 broad tags",
        "suggest 3-5 relevant follow-up",
        "suggest 3-5 follow-up questions",
        "summarizing the chat history",
        "categorizing the main themes",
        "<chat_history>",
    ]
    if any(m in _msg_lower for m in _marcadores_internos):
        if "generate a concise title" in _msg_lower:
            _resposta_interna = "MYRA task"
        elif "generate 1-3 broad tags" in _msg_lower:
            _resposta_interna = "MYRA, AI agent, automation"
        elif "suggest 3-5" in _msg_lower:
            _resposta_interna = "How does this work?; Can you explain the next step?; What should I try next?"
        else:
            _resposta_interna = "OK"
        return JSONResponse({
            "id": "chatcmpl-myra-internal",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": _resposta_interna}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    if not user_msg.strip():
        return JSONResponse({
            "id": "chatcmpl-myra",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Mensagem vazia."}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        })

    resposta_texto = await _myra_route_message(data, messages, user_msg, model)

    return JSONResponse({
        "id": f"chatcmpl-myra-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": resposta_texto}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    })


# FASE 29 — roteamento central do chat MYRA (substitui o Pipe removido)
_MYRA_CHAT_MEMORY_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MYRA" / "myra_openwebui_chat_memory.json"
_MYRA_CHAT_MEMORY_LOCK = threading.RLock()
_MYRA_CHAT_MAX_TURNS = 12
_MYRA_CHAT_MODEL = os.environ.get("MYRA_CHAT_MODEL", "qwen2.5:3b-instruct-q5_K_M")


def _myra_message_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content
                         if isinstance(part, dict) and isinstance(part.get("text"), str)).strip()
    return ""


def _myra_apply_identity_headers(data, headers):
    """Incorpora IDs de conversa/usuário quando um cliente os envia em headers."""
    if not isinstance(data, dict):
        data = {}
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    else:
        metadata = dict(metadata)

    chat_id = (
        metadata.get("chat_id") or metadata.get("conversation_id")
        or data.get("chat_id") or data.get("conversation_id")
    )
    user_id = metadata.get("user_id") or metadata.get("user") or data.get("user")
    if not chat_id:
        chat_id = (
            headers.get("x-openwebui-chat-id")
            or headers.get("x-chat-id")
            or headers.get("x-conversation-id")
        )
        if chat_id:
            metadata["chat_id"] = str(chat_id)[:256]
    if not user_id:
        user_id = headers.get("x-openwebui-user-id") or headers.get("x-user-id")
        if user_id:
            metadata["user_id"] = str(user_id)[:256]
    if metadata:
        data["metadata"] = metadata
    return data


def _myra_chat_key(data, messages=None):
    """Retorna uma chave de memória estável mesmo quando o provedor omite chat_id."""
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    chat_id = (
        metadata.get("chat_id")
        or metadata.get("conversation_id")
        or data.get("chat_id")
        or data.get("conversation_id")
    )
    user_id = metadata.get("user_id") or metadata.get("user") or data.get("user") or "local-user"
    if isinstance(user_id, dict):
        user_id = user_id.get("id") or user_id.get("email") or "local-user"
    if chat_id:
        return f"{user_id}:{chat_id}"

    # A API OpenAI-compatible do Open WebUI pode omitir o ID da conversa.
    # Nesse caso, ancoramos a chave na primeira mensagem do usuário, que permanece
    # no histórico enviado em turnos posteriores. Não usamos a última mensagem,
    # pois ela muda a cada turno. Conversas com a mesma abertura podem colidir;
    # quando o provedor fornece um ID explícito, ele sempre tem prioridade.
    first_user = next(
        (
            _myra_message_text(item.get("content"))
            for item in (messages or [])
            if isinstance(item, dict) and item.get("role") == "user"
            and _myra_message_text(item.get("content"))
        ),
        "",
    )
    if not first_user:
        return None
    fingerprint = hashlib.sha256(first_user.casefold().encode("utf-8")).hexdigest()[:20]
    return f"{user_id}:derived-{fingerprint}"


def _myra_memory_read():
    try:
        payload = json.loads(_MYRA_CHAT_MEMORY_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _myra_memory_turn(key, role, content):
    if not key or role not in {"user", "assistant"} or not str(content or "").strip():
        return
    with _MYRA_CHAT_MEMORY_LOCK:
        memory = _myra_memory_read()
        turns = memory.get(key, [])
        if not isinstance(turns, list):
            turns = []
        turns.append({"role": role, "content": str(content)[:3900], "ts": int(time.time())})
        memory[key] = turns[-(_MYRA_CHAT_MAX_TURNS * 2):]
        try:
            _MYRA_CHAT_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            temp = _MYRA_CHAT_MEMORY_PATH.with_suffix(".tmp")
            temp.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(_MYRA_CHAT_MEMORY_PATH)
        except OSError as exc:
            print(f"[CHAT-MEMORY] nao foi possivel salvar historico: {type(exc).__name__}")


def _myra_explicit_action(text):
    value = str(text or "").strip().lower()
    if value.endswith("?") or _re.match(
        r"^(como|o que|quem|qual|quais|por que|porque|quando|onde|how|what|who|which|why|when|where|can you explain|could you explain)\b",
        value,
    ):
        return False
    patterns = (
        r"^(por favor,?\s*)?(abra|abrir|abre|acessa|acesse|acessar|entre no|entra no|vai para|vá para|visite|navegue para|clique|clica|clicar|digite|digita|pesquise no google|pesquisa no google|pesquisar no google|pesquise (?:no )?youtube|pesquisa (?:no )?youtube|pesquisar (?:no )?youtube|busque (?:no )?youtube|buscar (?:no )?youtube|pesquise na web|pesquisa na web|pesquisar na web|procure no google|procura no google|procure na internet|busque na web|busca na web)\b",
        r"^(please\s+)?(open|launch|visit|go to|navigate to|click|type into|search google for|search the web for|look this up online)\b",
    )
    return any(_re.search(pattern, value) for pattern in patterns)


def _myra_control_intent(text):
    value = str(text or "").strip().lower()
    if _re.search(r"\b(status|estado)\b.*\b(tarefa|myra)\b|\b(como está|como esta|how is)\b.*\b(tarefa|task)\b", value):
        return "status"
    if _re.match(r"^(por favor,?\s*)?(cancele|cancelar|cancela|cancel|stop)\b.*\b(tarefa|task|execução|execucao|running)\b", value):
        return "cancel"
    if _re.match(r"^(por favor,?\s*)?(pause|pausar|pausa|suspenda|suspender)\b.*\b(tarefa|task|execução|execucao)\b", value):
        return "pause"
    if _re.match(r"^(por favor,?\s*)?(retome|retomar|resume|continue a tarefa|retomar tarefa)\b", value):
        match = _re.search(r"\b([A-Za-z0-9_.:-]{6,160})\b$", str(text).strip())
        return "resume:" + match.group(1) if match else "resume"
    return None


def _myra_rea_status_intent(text):
    """Detecta pedidos de status REA para consultar a ferramenta real."""
    value = str(text or "").casefold()
    value = _re.sub(r"[^a-z0-9_]+", " ", value)
    mentions_rea = bool(_re.search(r"\brea\b|\brea_status\b", value))
    asks_status = bool(_re.search(
        r"\b(status|verifique|verificar|consulte|consultar|disponibilidade|check|configuracao)\b",
        value,
    ))
    return mentions_rea and asks_status


def _myra_http_json(path, payload=None, timeout=30):
    url = "http://127.0.0.1:8000" + path
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"},
                                 method="GET" if payload is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result if isinstance(result, dict) else {"result": result}


def _myra_ollama_call(request):
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


async def _myra_route_message(data, messages, user_msg, model):
    key = _myra_chat_key(data, messages)
    incoming = []
    for item in messages[-24:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant", "system"}:
            continue
        content = _myra_message_text(item.get("content"))
        if content:
            incoming.append({"role": item["role"], "content": content[:3900]})
    conversation = [m for m in incoming if m["role"] in {"user", "assistant"}]
    persisted = _myra_memory_read().get(key, []) if key else []
    if len(conversation) > 1:
        history = conversation[-(_MYRA_CHAT_MAX_TURNS * 2):]
    else:
        history = [{"role": m.get("role"), "content": m.get("content", "")}
                   for m in persisted if isinstance(m, dict) and m.get("role") in {"user", "assistant"}]
        if conversation and (not history or history[-1] != conversation[-1]):
            history.append(conversation[-1])
        history = history[-(_MYRA_CHAT_MAX_TURNS * 2):]

    answer = ""
    control = _myra_control_intent(user_msg)
    time_query = _re.search(
        r"\b(que horas (?:são|sao)|qual (?:é o )?horário|horário atual|hora atual|me diga as horas|what time is it|what's the time|current time|tell me the time)\b",
        user_msg.strip().lower(),
    )

    if control:
        try:
            if control == "status":
                result = await asyncio.to_thread(_myra_http_json, "/task_status")
                answer = "\n".join([
                    f"Estado: {result.get('state', 'desconhecido')}",
                    f"Objetivo: {result.get('objetivo') or '—'}",
                    f"Passo: {result.get('passo_atual') or '—'}",
                    *([f"Erro: {result['erro']}"] if result.get("erro") else []),
                    *([f"Resultado: {result['resultado']}"] if result.get("resultado") else []),
                ])
            elif control == "cancel":
                result = await asyncio.to_thread(_myra_http_json, "/task_cancel", {})
                answer = str(result.get("result") or result.get("message") or "Cancelamento solicitado.")
            elif control == "pause":
                result = await asyncio.to_thread(_myra_http_json, "/task_pause", {})
                answer = str(result.get("result") or result.get("message") or "Pausa solicitada.")
            else:
                task_id = control.partition(":")[2]
                if not task_id or task_id.lower() in {"tarefa", "task", "retome", "retomar", "resume"}:
                    answer = "Para retomar uma tarefa pausada, informe também o ID da tarefa."
                elif not _re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", task_id):
                    answer = "O ID da tarefa contém caracteres inválidos."
                else:
                    result = await asyncio.to_thread(_myra_http_json, "/task_resume", {"task_id": task_id, "max_passos": 30})
                    answer = str(result.get("result") or result.get("message") or f"Retomada solicitada para {task_id}.")
        except Exception as exc:
            answer = f"Não consegui controlar a tarefa no backend local ({type(exc).__name__})."
    elif time_query:
        try:
            result = await asyncio.to_thread(_myra_http_json, "/get_current_time", {})
            answer = str(result.get("result") or result.get("hora") or "A ferramenta de horário não retornou um resultado.")
        except Exception as exc:
            answer = f"Não consegui consultar o horário atual ({type(exc).__name__})."
    elif _myra_rea_status_intent(user_msg):
        try:
            result = await asyncio.to_thread(
                _myra_http_json,
                "/task_simple",
                {"objetivo": user_msg[:1200], "max_passos": 5},
                1800,
            )
            if result.get("status") == "ok" and result.get("resultado_final"):
                answer = str(result["resultado_final"])
            else:
                answer = "A consulta REA nao foi concluida: " + str(
                    result.get("erro") or result.get("result") or result.get("status") or "sem detalhes"
                )
        except Exception as exc:
            answer = f"Falha ao consultar rea_status no backend local ({type(exc).__name__}: {str(exc)[:250]})."
    elif _myra_explicit_action(user_msg):
        try:
            current = await asyncio.to_thread(_myra_http_json, "/task_status")
            if current.get("state") == "running":
                answer = "Já existe uma tarefa em execução. " + str(current.get("objetivo") or "Consulte o status da tarefa atual.")
            else:
                # Mantém o pedido atual como objetivo; contexto só é anexado para referências curtas.
                contextual = _re.search(r"\b(isso|esse|essa|ele|ela|dessa|desse|agora|continue|do that|that|it)\b", user_msg.lower())
                objective = user_msg[:1200]
                if contextual:
                    previous = [m for m in history[:-1] if m.get("content")]
                    if previous:
                        compact = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in previous[-4:])
                        objective = f"CONTEXTO RECENTE DA CONVERSA:\n{compact}\n\nPEDIDO ATUAL:\n{objective}"
                # Usa a rota central já existente para manter um único ciclo de task,
                # estado, cancelamento, histórico e eventos do widget.
                result = await asyncio.to_thread(
                    _myra_http_json, "/task_simple", {"objetivo": objective, "max_passos": 15}, 1800
                )
                status = result.get("status", "desconhecido")
                if status == "ok":
                    answer = str(result.get("resultado_final") or "Tarefa concluída sem texto de resultado.")
                elif status == "pausado":
                    answer = f"Tarefa pausada. ID: {result.get('task_id') or 'não informado'}"
                elif status == "cancelado":
                    answer = "Tarefa cancelada."
                else:
                    answer = f"Tarefa {status}: {result.get('erro') or result.get('result') or 'sem detalhes'}"
        except Exception as exc:
            answer = f"Falha ao executar a ação ({type(exc).__name__}: {str(exc)[:300]})."
            _widget_set(state="error", terminado_em=time.time(), erro=answer)
    else:
        system = (
            "Você é MYRA, assistente pessoal local. Responda no idioma do usuário, de forma direta e natural. "
            "Use o histórico recente para entender referências como 'isso', 'continue' e perguntas de acompanhamento. "
            "Não afirme que executou ações sem confirmação real. Não invente fatos."
        )
        prompt_messages = [{"role": "system", "content": system}] + history[-24:]
        payload = {
            "model": _MYRA_CHAT_MODEL,
            "messages": prompt_messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 700},
        }
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            llm_result = await asyncio.to_thread(_myra_ollama_call, request)
            answer = str((llm_result.get("message") or {}).get("content") or "").strip()
            if not answer:
                answer = "O modelo local retornou uma resposta vazia."
        except Exception as exc:
            answer = f"Não consegui consultar o modelo local {_MYRA_CHAT_MODEL} ({type(exc).__name__})."

    if key:
        # Persiste somente o turno atual, sem duplicar o histórico que o cliente enviou.
        _myra_memory_turn(key, "user", user_msg)
        _myra_memory_turn(key, "assistant", answer)
    return answer



@app.get("/v1/models")
async def openai_list_models():
    """Lista modelos (formato OpenAI)."""
    return {
        "object": "list",
        "data": [{"id": "myra-agent", "object": "model", "created": int(time.time()), "owned_by": "myra"}]
    }

if __name__ == "__main__":
    import uvicorn
    # Keep the legacy local API bound to loopback. Remote access must go through
    # the dedicated Bearer-authenticated /remote/v1 routes and a private proxy.
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
