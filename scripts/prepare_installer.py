from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "installer" / "backend"
WHEELHOUSE = ROOT / "installer" / "wheelhouse"
RUNTIME = ROOT / "installer" / "runtime"
BROWSERS = ROOT / "installer" / "playwright-browsers"
PYTHON_URL = "https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.exe"
PYTHON_SHA256 = "92480239264744fe0386a1bd8275786fefa126e3129e56a68e22b52c73329965"
EXTENSION_FILES = (
    "manifest.json", "service_worker.js", "content.js", "offscreen.html",
    "offscreen.js", "popup.html", "popup.js", "README.md",
)


def copy_python_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*.py"):
        if "__pycache__" in path.parts or "backup" in path.name.lower() or ".bak" in path.name.lower():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_text(encoding="utf-8-sig")
        target.write_text("\n".join(line.rstrip() for line in content.splitlines()).rstrip() + "\n", encoding="utf-8")


def ensure_python_runtime() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    installer = RUNTIME / "python-3.14.10-amd64.exe"
    if not installer.is_file():
        print(f"Downloading official Python runtime: {PYTHON_URL}", flush=True)
        urllib.request.urlretrieve(PYTHON_URL, installer)
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    if digest != PYTHON_SHA256:
        raise RuntimeError(f"Python installer SHA-256 mismatch: {digest}")
    print(f"Verified Python installer ({installer.stat().st_size:,} bytes)", flush=True)


def build_offline_wheelhouse() -> None:
    if WHEELHOUSE.exists():
        shutil.rmtree(WHEELHOUSE)
    WHEELHOUSE.mkdir(parents=True)
    requirements = ROOT / "installer" / "requirements-core.lock"
    command = [sys.executable, "-m", "pip", "wheel", "--wheel-dir", str(WHEELHOUSE), "-r", str(requirements)]
    print("Building offline MYRA core wheelhouse...", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    wheels = list(WHEELHOUSE.glob("*.whl"))
    non_wheels = [p.name for p in WHEELHOUSE.iterdir() if p.is_file() and p.suffix != ".whl"]
    if not wheels or non_wheels:
        raise RuntimeError(f"Wheelhouse must contain wheels only. Non-wheel files: {non_wheels}")
    print(f"Prepared {len(wheels)} offline wheels ({sum(p.stat().st_size for p in wheels):,} bytes)", flush=True)


def install_playwright_browser() -> None:
    if BROWSERS.exists():
        shutil.rmtree(BROWSERS)
    BROWSERS.mkdir(parents=True)
    build_env = ROOT / "installer" / ".playwright-build-venv"
    if build_env.exists():
        shutil.rmtree(build_env)
    subprocess.run([sys.executable, "-m", "venv", str(build_env)], check=True)
    build_python = build_env / "Scripts" / "python.exe"
    subprocess.run([
        str(build_python), "-m", "pip", "install", "--no-index",
        "--find-links", str(WHEELHOUSE), "-r", str(ROOT / "installer" / "requirements-core.lock")
    ], check=True)
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS)
    print("Downloading Playwright Chromium for offline browser automation...", flush=True)
    subprocess.run([str(build_python), "-m", "playwright", "install", "chromium"], cwd=ROOT, env=env, check=True)
    subprocess.run([str(build_python), str(ROOT / "installer" / "smoke_browser_test.py")], cwd=ROOT, env=env, check=True)
    shutil.rmtree(build_env, ignore_errors=True)
    if not any(BROWSERS.iterdir()):
        raise RuntimeError("Playwright Chromium browser payload is empty.")
    size = sum(p.stat().st_size for p in BROWSERS.rglob("*") if p.is_file())
    print(f"Prepared Playwright browser payload ({size:,} bytes)", flush=True)


def main() -> None:
    if sys.version_info[:2] != (3, 14) or sys.platform != "win32":
        raise RuntimeError("Build the Windows installer with 64-bit Python 3.14 on Windows.")
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    shutil.copy2(ROOT / "agent.py", DEST / "agent.py")
    copy_python_tree(ROOT / "tasks", DEST / "tasks")
    copy_python_tree(ROOT / "computer", DEST / "computer")
    extension = DEST / "browser-extension"
    extension.mkdir()
    for name in EXTENSION_FILES:
        source = ROOT / "browser-extension" / name
        if source.is_file():
            shutil.copy2(source, extension / name)
    tools = DEST / "tools"
    tools.mkdir()
    helper = ROOT / "tools" / "rea_mcp_bridge.mjs"
    if helper.is_file():
        shutil.copy2(helper, tools / helper.name)
    shutil.copy2(ROOT / "requirements.txt", DEST / "requirements.txt")
    shutil.copy2(ROOT / "installer" / "requirements-core.txt", DEST / "requirements-core.txt")
    shutil.copy2(ROOT / "installer" / "requirements-core.lock", DEST / "requirements-core.lock")
    shutil.copy2(ROOT / "installer" / "requirements-vision.txt", DEST / "requirements-vision.txt")
    shutil.copy2(ROOT / "README.md", DEST / "README.md")
    ensure_python_runtime()
    build_offline_wheelhouse()
    install_playwright_browser()
    files = [p for p in DEST.rglob("*") if p.is_file()]
    forbidden = (".telegram", ".env", "backup", ".bak", "__pycache__")
    for path in files:
        relative = path.relative_to(DEST).as_posix().lower()
        if any(token in relative for token in forbidden):
            raise RuntimeError(f"Private or backup file entered installer payload: {relative}")
    print(f"Prepared {len(files)} safe backend files in {DEST}", flush=True)


if __name__ == "__main__":
    main()
