import time

from tasks import cancel_state
from tasks.browser_bridge import browser_wait


def test_browser_wait_stops_at_pause_checkpoint():
    cancel_state.resetar()
    cancel_state.resetar_pausa()
    cancel_state.marcar_pausada()
    started = time.monotonic()
    try:
        result = browser_wait(5000)
        assert result["status"] == "pausado"
        assert time.monotonic() - started < 0.5
    finally:
        cancel_state.resetar_pausa()
        cancel_state.resetar()


def test_browser_wait_stops_at_cancel_checkpoint():
    cancel_state.resetar()
    cancel_state.resetar_pausa()
    cancel_state.marcar_cancelada()
    started = time.monotonic()
    try:
        result = browser_wait(5000)
        assert result["status"] == "cancelado"
        assert time.monotonic() - started < 0.5
    finally:
        cancel_state.resetar()
        cancel_state.resetar_pausa()
