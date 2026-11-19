"""
Screen Capture - tira screenshot via mss.
"""
import mss
import os
import datetime
from pathlib import Path


SCREENSHOTS_DIR = os.environ.get("MYRA_SCREENSHOTS", str(Path(os.environ.get("MYRA_DATA_DIR", Path(__file__).resolve().parents[1])) / "screenshots"))


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
