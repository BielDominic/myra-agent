"""
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
