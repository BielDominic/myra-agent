import os

pasta = r"C:\computer-agent\computer"
os.makedirs(pasta, exist_ok=True)

# __init__.py
with open(os.path.join(pasta, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("")

# controller.py
controller = '''"""
Computer Controller - controla mouse e teclado via pyautogui.
"""
import pyautogui
import time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def move_mouse(x: int, y: int, duration: float = 0.3) -> dict:
    """Move o mouse para (x, y) com animacao suave."""
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return {"status": "ok", "result": f"Mouse movido para ({x}, {y})"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def click(x: int = None, y: int = None, button: str = "left") -> dict:
    """Clica em (x, y) ou na posicao atual."""
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(button=button)
        return {"status": "ok", "result": f"Clique {button} em ({x}, {y})"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def double_click(x: int = None, y: int = None) -> dict:
    """Duplo clique em (x, y)."""
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.doubleClick()
        return {"status": "ok", "result": f"Duplo clique em ({x}, {y})"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def right_click(x: int = None, y: int = None) -> dict:
    """Clique direito em (x, y)."""
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.rightClick()
        return {"status": "ok", "result": f"Clique direito em ({x}, {y})"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def type_text(text: str, interval: float = 0.02) -> dict:
    """Digita texto."""
    try:
        pyautogui.write(text, interval=interval)
        return {"status": "ok", "result": f"Texto digitado: {text[:50]!r}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def press_key(key: str) -> dict:
    """Pressiona uma tecla (ex: 'enter', 'tab', 'esc')."""
    try:
        pyautogui.press(key)
        return {"status": "ok", "result": f"Tecla pressionada: {key}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def hotkey(*keys: str) -> dict:
    """Pressiona combinacao de teclas (ex: 'ctrl', 'c')."""
    try:
        pyautogui.hotkey(*keys)
        return {"status": "ok", "result": f"Hotkey: {'+'.join(keys)}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}


def scroll(amount: int) -> dict:
    """Rola a tela (positivo = cima, negativo = baixo)."""
    try:
        pyautogui.scroll(amount)
        return {"status": "ok", "result": f"Scroll: {amount}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}
'''

with open(os.path.join(pasta, "controller.py"), "w", encoding="utf-8") as f:
    f.write(controller)

# screen.py
screen = '''"""
Screen Capture - tira screenshot via mss.
"""
import mss
import os
import datetime


SCREENSHOTS_DIR = r"C:\\computer-agent\\screenshots"


def screenshot(salvar: bool = True) -> dict:
    """Tira screenshot da tela inteira. Retorna o caminho do arquivo."""
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)

        if salvar:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = os.path.join(SCREENSHOTS_DIR, f"screen_{timestamp}.png")
            mss.tools.to_png(img.rgb, img.size, output=caminho)
            return {"status": "ok", "result": f"Screenshot salvo em {caminho}", "path": caminho}
        else:
            return {"status": "ok", "result": "Screenshot tirado (nao salvo)"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}
'''

with open(os.path.join(pasta, "screen.py"), "w", encoding="utf-8") as f:
    f.write(screen)

# windows.py
windows = '''"""
Windows - lista janelas abertas via pygetwindow.
"""
import pygetwindow as gw


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


def focus_window(titulo: str) -> dict:
    """Foca uma janela pelo titulo (parcial)."""
    try:
        janelas = gw.getWindowsWithTitle(titulo)
        if not janelas:
            return {"status": "erro", "result": f"Janela nao encontrada: {titulo}"}
        janelas[0].activate()
        return {"status": "ok", "result": f"Janela focada: {janelas[0].title}"}
    except Exception as e:
        return {"status": "erro", "result": f"{type(e).__name__}: {e}"}
'''

with open(os.path.join(pasta, "windows.py"), "w", encoding="utf-8") as f:
    f.write(windows)

print("[OK] Pasta computer/ criada com 4 arquivos")
print("  - computer/__init__.py")
print("  - computer/controller.py")
print("  - computer/screen.py")
print("  - computer/windows.py")