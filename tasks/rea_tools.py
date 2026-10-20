"""Integracao opcional com REA (Reverse Engineer Anything).

A analise so roda quando o usuario invoca a ferramenta; nenhuma instalacao global
ou analise automatica acontece no startup. Por seguranca, o alvo precisa estar
dentro de uma raiz explicitamente permitida.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

REA_PACKAGE = os.getenv("MYRA_REA_PACKAGE", "rea-agents@6.5.0")
WORKSPACE = Path(os.getenv("MYRA_WORKSPACE", r"C:\computer-agent\workspace"))
MAX_OUTPUT_CHARS = 12_000


def _allowed_roots() -> list[Path]:
    raw = os.getenv("MYRA_REA_ALLOWED_ROOTS", "").strip()
    values = [part.strip().strip('"') for part in raw.split(os.pathsep) if part.strip()]
    roots = [Path(value).expanduser().resolve(strict=False) for value in values]
    if not roots:
        roots = [WORKSPACE.expanduser().resolve(strict=False)]
    return roots


def _resolve_target(target: str) -> Path:
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Informe o caminho de uma pasta de aplicacao JavaScript.")
    path = Path(target).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError("O alvo precisa ser uma pasta existente, nao um arquivo.")
    if not any(path == root or root in path.parents for root in _allowed_roots()):
        raise PermissionError(
            "Alvo fora das raizes autorizadas. Configure MYRA_REA_ALLOWED_ROOTS "
            "com pastas que voce tem permissao para analisar."
        )
    if not any((path / name).exists() for name in ("package.json", "index.html", "src", "dist", "build")):
        raise ValueError("A pasta nao parece ser um projeto JavaScript (package.json/src/dist nao encontrado).")
    return path


def _node_version() -> tuple[int, int, int]:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js nao encontrado no PATH. Instale Node.js 22.19+ ou 24.11+.")
    result = subprocess.run(
        [node, "--version"], capture_output=True, text=True, timeout=10,
        encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Nao foi possivel consultar a versao do Node.js.")
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", result.stdout.strip())
    if not match:
        raise RuntimeError(f"Versao do Node.js inesperada: {result.stdout.strip()[:80]}")
    version = tuple(int(part) for part in match.groups())
    major, minor, _patch = version
    supported = (
        (major == 22 and (minor, _patch) >= (19, 0))
        or (major == 24 and (minor, _patch) >= (11, 0))
        or major >= 26
    )
    if not supported:
        raise RuntimeError(
            f"Node.js {'.'.join(map(str, version))} nao suportado pelo REA; "
            "use 22.19+, 24.11+ ou 26+ (Node 23/25 nao sao suportados)."
        )
    return version


def _npx_command() -> list[str]:
    """Prefere executar o CLI JS diretamente para evitar shell/cmd injection."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js nao encontrado no PATH.")
    node_dir = Path(node).resolve().parent
    candidates = (
        node_dir / "node_modules" / "npm" / "bin" / "npx-cli.js",
        node_dir / "node_modules" / "npm" / "bin" / "npx.js",
    )
    for cli in candidates:
        if cli.is_file():
            return [node, str(cli)]
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx nao encontrado. Reinstale o npm junto do Node.js.")
    return [npx]


def rea_analyze_javascript(target: str) -> dict:
    """Analisa estaticamente um projeto JavaScript local autorizado usando REA."""
    try:
        path = _resolve_target(target)
        version = _node_version()
        command = _npx_command() + [
            "--yes", REA_PACKAGE, "analyze-javascript-application", str(path), "--json"
        ]
        completed = subprocess.run(
            command,
            cwd=str(path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
            check=False,
            shell=False,
        )
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f"REA encerrou com codigo {completed.returncode}."
            return {"status": "erro", "result": detail[:3000], "returncode": completed.returncode}
        if not stdout:
            return {"status": "erro", "result": "REA terminou sem retornar evidencias."}
        return {
            "status": "ok",
            "result": stdout[:MAX_OUTPUT_CHARS],
            "truncated": len(stdout) > MAX_OUTPUT_CHARS,
            "node_version": ".".join(map(str, version)),
            "rea_package": REA_PACKAGE,
            "target": str(path),
        }
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": "A analise REA excedeu 240 segundos e foi encerrada."}
    except Exception as exc:
        return {"status": "erro", "result": f"{type(exc).__name__}: {exc}"}


def rea_status() -> dict:
    """Verifica pre-requisitos locais sem instalar nem executar o REA."""
    node = shutil.which("node")
    npx = shutil.which("npx")
    result = {"status": "ok" if node and npx else "aviso", "node_found": bool(node), "npx_found": bool(npx)}
    if node:
        try:
            result["node_version"] = subprocess.run(
                [node, "--version"], capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace", check=False,
            ).stdout.strip()
        except Exception:
            result["node_version"] = "indisponivel"
    result["rea_package"] = REA_PACKAGE
    result["allowed_roots"] = [str(path) for path in _allowed_roots()]
    result["note"] = "O pacote REA so sera baixado pelo npx quando rea_analyze_javascript for chamado."
    return result


def registrar_todas(registrar_ferramenta: Callable) -> None:
    registrar_ferramenta(
        "rea_analyze_javascript",
        rea_analyze_javascript,
        "Analisa a estrutura e evidencias de um app JavaScript/Electron autorizado usando REA. "
        "Obrigatorio: target com caminho de pasta dentro de MYRA_REA_ALLOWED_ROOTS. "
        "Use somente para engenharia reversa autorizada; nao instala dependencias globalmente."
    )
    registrar_ferramenta(
        "rea_status",
        rea_status,
        "Verifica se Node.js/npx e as raizes autorizadas estao configurados para a integracao REA, sem instalar nada."
    )
