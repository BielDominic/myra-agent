from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_error_view_offers_copy_and_retry():
    html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    assert 'id="btn-copy-error"' in html
    assert 'id="btn-retry-error"' in html
    assert "async function copyError()" in js
    assert "async function retryFailedTask()" in js
    assert "await runMyraObjective(objective)" in js


def test_user_facing_progress_strings_are_not_mojibake():
    js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    for bad in ("descri??o", "Pausando?", "Conclu?da", "n?o apareceu", "hist?rico local"):
        assert bad not in js
