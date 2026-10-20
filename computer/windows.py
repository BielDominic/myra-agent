"""
Windows - lista janelas abertas via pygetwindow.
"""
import pygetwindow as gw
import ctypes
from ctypes import wintypes


# Constantes do Windows
user32 = ctypes.windll.user32
SW_RESTORE = 9
SW_SHOW = 5
SW_MINIMIZE = 6


def get_windows() -> dict:
    """Retorna lista de janelas abertas (titulo)."""
    try:
        titulos = [w.title for w in gw.getAllWindows() if w.title.strip()]
        return {"status": "ok", "result": titulos}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def get_active_window() -> dict:
    """Retorna o titulo da janela ativa."""
    try:
        w = gw.getActiveWindow()
        return {"status": "ok", "result": w.title if w else "Nenhuma"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def _focus_by_title_ctypes(titulo: str) -> bool:
    """
    Foca uma janela usando a API nativa do Windows (mais robusto que pygetwindow).
    Retorna True se conseguiu focar.
    """
    encontrada_hwnd = [None]

    # Callback pra cada janela
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        titulo_janela = buff.value

        if titulo.lower() in titulo_janela.lower():
            encontrada_hwnd[0] = hwnd
            return False  # para a enumeracao

        return True

    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    hwnd = encontrada_hwnd[0]
    if hwnd is None:
        return False

    # Se minimizada, restaura
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    # Traz pra frente
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)
    return True


def focus_window(titulo: str) -> dict:
    """Foca uma janela pelo titulo (parcial). Usa API nativa do Windows."""
    try:
        if _focus_by_title_ctypes(titulo):
            return {"status": "ok", "result": f"Janela focada: {titulo}"}

        # Fallback: tenta com pygetwindow
        try:
            janelas = gw.getWindowsWithTitle(titulo)
            if not janelas:
                return {"status": "erro", "result": f"Janela nao encontrada: {titulo}"}
            janela = janelas[0]
            if janela.isMinimized:
                janela.restore()
            janela.activate()
            return {"status": "ok", "result": f"Janela focada (fallback): {janela.title}"}
        except Exception as e2:
            return {"status": "erro", "result": f"Janela nao encontrada: {titulo} ({type(e2).__name__})"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}