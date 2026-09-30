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
import re as _re
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

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# ============================================================
# CONFIRMACAO PENDENTE (FASE 8)
# ============================================================
pending_confirmation = None  # {"acao": ..., "detalhes": ..., "timestamp": ..., "confirmada": False}
CONFIRMATION_TIMEOUT = 300  # 5 minutos em segundos


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
    cidade: str = "Dublin"


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

    # BLOQUEIO ANTI-LOOP: se ja existe uma pendencia recente, NAO cria outra
    if pending_confirmation is not None:
        idade = time.time() - pending_confirmation["timestamp"]
        if idade < CONFIRMATION_TIMEOUT:
            # Pendencia ainda valida - NAO cria nova
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
            # Pendencia expirou - limpa e cria nova
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
    """Executa a acao que estava pendente de confirmacao."""
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
        return {"status": "erro", "result": "Nenhuma acao pendente configurada. Use request_confirmation com acao_pendente e parametros."}

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


# ============================================================
# EMAIL (IMAP/SMTP)
# ============================================================

def _conectar_imap():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise Exception("GMAIL_USER ou GMAIL_APP_PASSWORD nao configurados")
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return mail


def _get_trash_folder(mail):
    """Detecta o nome da pasta Lixeira do Gmail (Trash, Lixeira, Papelera, etc)."""
    try:
        status, pastas = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"

        for pasta in pastas:
            nome = pasta.decode("utf-8", errors="ignore")
            # Procura por \Trash (flag oficial do IMAP)
            if "\\Trash" in nome:
                # Extrai o nome entre as ultimas aspas
                partes = nome.split('"')
                if len(partes) >= 2:
                    return partes[-2]
        return "[Gmail]/Trash"
    except Exception:
        return "[Gmail]/Trash"


def _get_trash_folder(mail):
    """Detecta o nome da pasta Lixeira do Gmail (Trash, Lixeira, Papelera, etc)."""
    try:
        status, pastas = mail.list()
        if status != "OK":
            return "[Gmail]/Trash"

        for pasta in pastas:
            nome = pasta.decode("utf-8", errors="ignore")
            # Procura por \Trash (flag oficial do IMAP)
            if "\\Trash" in nome:
                # Extrai o nome entre as ultimas aspas
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
    global pending_confirmation
    print(f"[EMAIL_SEND] para={data.para!r} assunto={data.assunto!r} corpo={data.corpo[:50]!r}")

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
    print(f"[EMAIL_MARK_READ] indice={data.indice} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "+FLAGS", "\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_READ] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_mark_unread")
def email_mark_unread(data: EmailMark):
    print(f"[EMAIL_MARK_UNREAD] indice={data.indice} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.store(eid, "-FLAGS", "\\Seen")
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} marcado como NAO lido"}
    except Exception as e:
        print(f"[EMAIL_MARK_UNREAD] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_move")
def email_move(data: EmailMove):
    print(f"[EMAIL_MOVE] indice={data.indice} origem={data.pasta_origem} destino={data.pasta_destino}")
    try:
        mail = _conectar_imap()
        trash = _get_trash_folder(mail)
        mail.select(data.pasta_origem)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, data.pasta_destino)
        mail.store(eid, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} movido de {data.pasta_origem} para {data.pasta_destino}"}
    except Exception as e:
        print(f"[EMAIL_MOVE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_delete")
def email_delete(data: EmailDelete):
    global pending_confirmation
    print(f"[EMAIL_DELETE] indice={data.indice} pasta={data.pasta}")

    try:
        mail = _conectar_imap()
        trash = _get_trash_folder(mail)
        mail.select(data.pasta)
        status, mensagens = mail.search(None, "ALL")
        ids = mensagens[0].split()
        ids_recentes = ids[::-1]

        if data.indice >= len(ids_recentes):
            return {"status": "erro", "result": f"Indice {data.indice} fora do range (tem {len(ids_recentes)} emails)"}

        eid = ids_recentes[data.indice]
        mail.copy(eid, trash)
        mail.store(eid, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return {"status": "ok", "result": f"Email {data.indice} movido para a Lixeira (Trash)"}
    except Exception as e:
        print(f"[EMAIL_DELETE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


@app.post("/email_search")
def email_search(data: EmailSearch):
    print(f"[EMAIL_SEARCH] termo={data.termo!r} pasta={data.pasta}")
    try:
        mail = _conectar_imap()
        mail.select(data.pasta)
        # Busca por assunto OU corpo
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
    global pending_confirmation
    print(f"[EMAIL_REPLY] indice={data.indice} pasta={data.pasta}")

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
        msg_original = email_lib.message_from_bytes(dados[0][1])

        assunto_original = _decodificar(msg_original.get("Subject", ""))
        de_original = msg_original.get("From", "")
        message_id_original = msg_original.get("Message-ID", "")

        mail.logout()

        # Envia a resposta via SMTP
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


# ============================================================
# UTILITARIAS
# ============================================================

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
    print(f"[GET_WEATHER] cidade={data.cidade}")
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(data.cidade)}&count=1&language=pt&format=json"
        with urllib.request.urlopen(geo_url, timeout=10) as r:
            geo = json.loads(r.read().decode())

        if not geo.get("results"):
            return {"status": "erro", "result": f"Cidade '{data.cidade}' nao encontrada"}

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


# ============================================================
# ARQUIVOS
# ============================================================

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


# ============================================================
# WEB SEARCH (DuckDuckGo HTML)
# ============================================================

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


# ============================================================
# SCREENSHOT
# ============================================================

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


# ============================================================
# VISAO (analisa screenshot via llama-server)
# ============================================================

@app.post("/see")
def see(data: SeeImage):
    start_browser()
    print("[SEE] analisando screenshot...")
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo = os.path.join(SCREENSHOTS_DIR, f"see_{agora}.png")
        page.screenshot(path=arquivo, full_page=False)
        print(f"[SEE] screenshot salvo em {arquivo}")

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

        # Corrige encoding duplamente codificado (UTF-8 -> Latin-1 -> UTF-8)
        if conteudo:
            substituicoes = {
                "Ã©": "é", "Ã¡": "á", "Ã£": "ã", "Ã¢": "â", "Ãª": "ê",
                "Ã": "í", "Ã³": "ó", "Ã´": "ô", "Ãµ": "õ", "Ãº": "ú",
                "Ã¼": "ü", "Ã§": "ç", "Ã±": "ñ",
                "Ã‰": "É", "Ã": "Á", "Ãƒ": "Ã", "ÃŠ": "Ê",
                "Ã": "Í", "Ã“": "Ó", "Ã”": "Ô", "Ã•": "Õ", "Ãš": "Ú",
                "Ã‡": "Ç", "Ã‚": "Â",
            }
            for errado, certo in substituicoes.items():
                conteudo = conteudo.replace(errado, certo)

        print(f"[SEE] resposta: {conteudo[:100]}...")
        return {"status": "ok", "result": conteudo, "screenshot": arquivo}
    except Exception as e:
        print(f"[SEE] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}

# ============================================================
# FASE 15 - Ferramentas de arquivo avancadas
# ============================================================

@app.post("/delete_file")
def delete_file(data: DeleteFile):
    global pending_confirmation
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
    global pending_confirmation
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

        return {"status": "ok", "result": f"{len(resultados)} ocorrencia(s):\n" + "\n".join(resultados)}
    except Exception as e:
        print(f"[SEARCH_IN_FILES] ERRO: {e}")
        return {"status": "erro", "result": f"Erro: {type(e).__name__}: {e}"}


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
