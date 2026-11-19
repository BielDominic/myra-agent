from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "installer" / "backend"
EXTENSION_FILES = (
    "manifest.json",
    "service_worker.js",
    "content.js",
    "offscreen.html",
    "offscreen.js",
    "popup.html",
    "popup.js",
    "README.md",
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


def main() -> None:
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
    shutil.copy2(ROOT / "README.md", DEST / "README.md")

    files = [p for p in DEST.rglob("*") if p.is_file()]
    forbidden = (".telegram", ".env", "backup", ".bak", "__pycache__")
    for path in files:
        relative = path.relative_to(DEST).as_posix().lower()
        if any(token in relative for token in forbidden):
            raise RuntimeError(f"Private or backup file entered installer payload: {relative}")
    print(f"Prepared {len(files)} safe backend files in {DEST}")


if __name__ == "__main__":
    main()
