"""
MYRA Widget ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Island flutuante com altura DINAMICA via Win32.
Transparencia real via WS_EX_LAYERED + LWA_COLORKEY (chroma key).
Chromakey so fica ativo em idle (pilula). Em card, e removido
pra devolver os cliques a janela.
"""
import sys
import json
import time
import urllib.request
import threading
import ctypes
from ctypes import wintypes
import webview
from pathlib import Path

AGENT_URL = "http://127.0.0.1:8000"

IDLE_WIDTH = 200
IDLE_HEIGHT = 44
CARD_WIDTH = 440
CARD_HEIGHT = 340
TOP_MARGIN = 40
OFFSET_X = -155

BACKGROUND_COLOR_HEX = "#0a0a15"
BACKGROUND_COLOR_WIN32 = 0x00150a0a

WIDGET_DIR = Path(__file__).parent.resolve()
INDEX_HTML = WIDGET_DIR / "index.html"


def _declarar_win32():
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    user32.SetLayeredWindowAttributes.argtypes = [
        wintypes.HWND, ctypes.c_uint, ctypes.c_byte, ctypes.c_uint
    ]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL


def _aplicar_transparencia(hwnd):
    if not hwnd:
        print("[TRANSP] HWND invalido")
        return False
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    LWA_COLORKEY = 0x00000001
    user32 = ctypes.windll.user32
    try:
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        ok = user32.SetLayeredWindowAttributes(
            hwnd, BACKGROUND_COLOR_WIN32, 0, LWA_COLORKEY
        )
        if ok:
            print(f"[TRANSP] chroma key aplicado: {BACKGROUND_COLOR_HEX}")
        return bool(ok)
    except Exception as e:
        print(f"[TRANSP] erro: {e}")
        return False


def _remover_transparencia(hwnd):
    if not hwnd:
        return False
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    user32 = ctypes.windll.user32
    try:
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex & ~WS_EX_LAYERED)
        print("[TRANSP] chroma key removido (cliques liberados)")
        return True
    except Exception as e:
        print(f"[TRANSP] erro ao remover: {e}")
        return False


def get_hwnd_from_title(title="MYRA"):
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, title)
    if hwnd:
        return hwnd
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value.strip() == title:
                found.append(hwnd)
        return True
    user32.EnumWindows(enum_proc, 0)
    return found[0] if found else 0


def resize_window_win32(hwnd, width, height):
    user32 = ctypes.windll.user32
    screen_width, _ = get_screen_size()
    centro = (screen_width - width) // 2
    x_pos = centro + OFFSET_X

    # Remove WS_CAPTION e WS_THICKFRAME (altura minima do Form)
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_SYSMENU = 0x00080000
    try:
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        novo_style = style & ~WS_CAPTION & ~WS_THICKFRAME & ~WS_SYSMENU
        if novo_style != style:
            user32.SetWindowLongW(hwnd, GWL_STYLE, novo_style)
    except Exception:
        pass

    # MoveWindow FORCA o resize (SetWindowPos e ignorado pelo pywebview)
    user32.MoveWindow.argtypes = [
        wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.BOOL,
    ]
    user32.MoveWindow.restype = wintypes.BOOL
    user32.MoveWindow(hwnd, x_pos, TOP_MARGIN, width, height, True)

def _preparar_janela(hwnd):
    _aplicar_transparencia(hwnd)
    resize_window_win32(hwnd, IDLE_WIDTH, IDLE_HEIGHT)
    print(f"[MONITOR] resize inicial: pilula {IDLE_WIDTH}x{IDLE_HEIGHT}")


class StatusMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._stop = False
        self._last_state = None
        self._hwnd = None

    def stop(self):
        self._stop = True

    def run(self):
        for _ in range(150):
            if self._stop:
                return
            self._hwnd = get_hwnd_from_title("MYRA")
            if self._hwnd:
                break
            time.sleep(0.1)
        if not self._hwnd:
            print("[MONITOR] nao achei a janela MYRA")
            return
        print(f"[MONITOR] HWND encontrado: {self._hwnd}")

        time.sleep(0.5)
        _preparar_janela(self._hwnd)
        time.sleep(1.0)
        _preparar_janela(self._hwnd)

        while not self._stop:
            if self._last_state in (None, "idle"):
                _aplicar_transparencia(self._hwnd)
                for _ in range(3):
                    resize_window_win32(self._hwnd, IDLE_WIDTH, IDLE_HEIGHT)
                    time.sleep(0.05)
            else:
                _remover_transparencia(self._hwnd)
                for _ in range(10):
                    resize_window_win32(self._hwnd, CARD_WIDTH, CARD_HEIGHT)
                    time.sleep(0.05)

            try:
                req = urllib.request.Request(f"{AGENT_URL}/task_status", method="GET")
                with urllib.request.urlopen(req, timeout=3) as r:
                    status = json.loads(r.read().decode("utf-8"))
                state = status.get("state", "idle")
                if state != self._last_state:
                    print(f"[MONITOR] state: {self._last_state} -> {state}")
                    self._last_state = state

                    # FORCA resize imediatamente quando o state muda
                    if state in (None, "idle"):
                        _aplicar_transparencia(self._hwnd)
                        for _ in range(20):
                            resize_window_win32(self._hwnd, IDLE_WIDTH, IDLE_HEIGHT)
                            time.sleep(0.03)
                    else:
                        _remover_transparencia(self._hwnd)
                        for _ in range(20):
                            resize_window_win32(self._hwnd, CARD_WIDTH, CARD_HEIGHT)
                            time.sleep(0.03)
            except Exception:
                pass
            time.sleep(0.1)


def enable_dpi_awareness():
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass


def get_screen_size():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def get_center_position(width):
    screen_width, _ = get_screen_size()
    centro = (screen_width - width) // 2
    return centro + OFFSET_X


def main():
    print("=== MYRA Widget ===")
    print(f"HTML: {INDEX_HTML}")
    if not INDEX_HTML.exists():
        print(f"ERRO: {INDEX_HTML} nao existe!")
        sys.exit(1)
    _declarar_win32()
    enable_dpi_awareness()
    screen_width, screen_height = get_screen_size()
    x_pos = get_center_position(IDLE_WIDTH)
    print(f"Tela: {screen_width}x{screen_height}")
    print(f"Janela inicial: {IDLE_WIDTH}x{IDLE_HEIGHT} em ({x_pos}, {TOP_MARGIN})")

    window = webview.create_window(
        title="MYRA",
        url=str(INDEX_HTML),
        width=IDLE_WIDTH,
        height=IDLE_HEIGHT,
        x=x_pos,
        y=TOP_MARGIN,
        resizable=False,
        frameless=True,
        easy_drag=False,
        background_color="#0a0a15",
    )

    def _on_loaded():
        time.sleep(0.5)
        hwnd = get_hwnd_from_title("MYRA")
        if hwnd:
            _preparar_janela(hwnd)
            print("[LOADED] resize aplicado pos-load")

    window.events.loaded += _on_loaded

    monitor = StatusMonitor()
    monitor.start()
    try:
        webview.start(debug=False)
    finally:
        monitor.stop()
        print("Widget fechado.")


if __name__ == "__main__":
    main()