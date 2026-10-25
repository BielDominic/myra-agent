"""Integracao opcional com REA (Reverse Engineer Anything).

A analise so roda quando o usuario invoca a ferramenta; nenhuma instalacao global
ou analise automatica acontece no startup. Por seguranca, o alvo precisa estar
dentro de uma raiz explicitamente permitida.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

REA_PACKAGE = os.getenv("MYRA_REA_PACKAGE", "rea-agents@6.5.0")
WORKSPACE = Path(os.getenv("MYRA_WORKSPACE", r"C:\computer-agent\workspace"))
MAX_OUTPUT_CHARS = 12_000
MCP_HELPER = Path(__file__).resolve().parents[1] / "tools" / "rea_mcp_bridge.mjs"
MCP_TIMEOUT_SECONDS = 90
MCP_LONG_TIMEOUT_MS = 240_000
MCP_MAX_TIMEOUT_SECONDS = 330
REA_MCP_LONG_RUNNING_TOOLS = frozenset({
    "address_name",
    "inspect_native_instruction",
    "inspect_native_data_type",
    "inspect_native_load_image",
    "resolve_native_call_targets",
})
ACTIVE_TARGET_FILE = WORKSPACE / ".myra_rea_active_target.json"
# Allowlist excludes mutation/execution tools and validates every local target path.
REA_MCP_READ_ONLY_TOOLS = frozenset({
    "analyze_javascript_application",
    "open_binary",
    "inspect_binary_layout",
    "inspect_go_binary",
    "inspect_rust_binary",
    "current_document",
    "current_address",
    "current_procedure",
    "address_name",
    "comment",
    "inline_comment",
    "inspect_native_instruction",
    "inspect_native_data_type",
    "inspect_native_load_image",
    "resolve_native_call_targets",
})


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


def rea_catalog() -> dict:
    """Consulta o catalogo de comandos REA suportados pela versao configurada."""
    try:
        _node_version()
        command = _npx_command() + [
            "--yes", REA_PACKAGE, "--llms", "--format", "json"
        ]
        completed = subprocess.run(
            command,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
            shell=False,
        )
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        if completed.returncode != 0:
            detail = stderr or stdout or f"REA encerrou com codigo {completed.returncode}."
            return {"status": "erro", "result": detail[:3000], "returncode": completed.returncode}
        if not stdout:
            return {"status": "erro", "result": "REA terminou sem retornar o catalogo."}
        try:
            payload = json.loads(stdout)
        except ValueError:
            return {"status": "erro", "result": "REA retornou um catalogo que nao e JSON valido.", "output": stdout[:3000]}
        commands = payload.get("commands") if isinstance(payload, dict) else None
        if not isinstance(commands, list):
            return {"status": "erro", "result": "O JSON do REA nao contem uma lista commands valida."}
        catalog = []
        for item in commands:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                catalog.append({
                    "name": item["name"][:120],
                    "description": str(item.get("description", ""))[:500],
                })
        return {
            "status": "ok",
            "rea_package": REA_PACKAGE,
            "catalog_version": payload.get("version"),
            "command_count": len(catalog),
            "commands": catalog[:250],
            "truncated": len(catalog) > 250,
        }
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": "A consulta ao catalogo REA excedeu 60 segundos."}
    except Exception as exc:
        return {"status": "erro", "result": f"{type(exc).__name__}: {exc}"}


def _run_mcp_bridge(mode: str, payload: dict | None = None) -> dict:
    """Executa o cliente MCP isolado e devolve apenas JSON validado."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js nao encontrado no PATH.")
    if not MCP_HELPER.is_file():
        raise RuntimeError(f"Helper MCP nao encontrado: {MCP_HELPER}")
    request_payload = payload or {}
    timeout_ms = request_payload.get("timeoutMs") if isinstance(request_payload, dict) else None
    timeout_seconds = MCP_TIMEOUT_SECONDS
    if isinstance(timeout_ms, int) and not isinstance(timeout_ms, bool) and 1000 <= timeout_ms <= 300000:
        timeout_seconds = min(MCP_MAX_TIMEOUT_SECONDS, max(MCP_TIMEOUT_SECONDS, (timeout_ms + 999) // 1000 + 20))
    request = json.dumps(request_payload, ensure_ascii=False)
    completed = subprocess.run(
        [node, str(MCP_HELPER), mode],
        input=request if mode == "call" else "",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
        shell=False,
        cwd=str(WORKSPACE),
    )
    stdout = (completed.stdout or "").strip()
    if not stdout:
        detail = (completed.stderr or "").strip()
        raise RuntimeError((detail or "O cliente MCP nao retornou JSON.")[:3000])
    try:
        result = json.loads(stdout.splitlines()[-1])
    except ValueError as exc:
        raise RuntimeError("Resposta MCP nao e JSON valido.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Resposta MCP tem formato invalido.")
    if completed.returncode != 0 or result.get("status") != "ok":
        raise RuntimeError(str(result.get("result") or completed.stderr or "Falha MCP.")[:3000])
    return result


def rea_mcp_list_tools() -> dict:
    """Descobre ferramentas e esquemas MCP reais, expondo esquemas apenas para allowlist."""
    try:
        payload = _run_mcp_bridge("list")
        tools = payload.get("tools")
        if not isinstance(tools, list):
            return {"status": "erro", "result": "Resposta tools/list invalida."}
        catalog = []
        safe_tools = []
        for item in tools:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            entry = {"name": item["name"][:120], "description": str(item.get("description", ""))[:500]}
            catalog.append(entry)
            if item["name"] in REA_MCP_READ_ONLY_TOOLS:
                safe_tools.append({**entry, "inputSchema": item.get("inputSchema", {})})
        return {
            "status": "ok",
            "rea_package": REA_PACKAGE,
            "tool_count": len(catalog),
            "tools": catalog[:250],
            "read_only_tools": safe_tools,
            "truncated": len(catalog) > 250,
        }
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": f"A descoberta MCP excedeu {MCP_TIMEOUT_SECONDS} segundos."}
    except Exception as exc:
        return {"status": "erro", "result": f"{type(exc).__name__}: {exc}"}


def rea_mcp_call(tool_name: str, arguments: dict | None = None, **direct_arguments) -> dict:
    """Chama uma ferramenta MCP autorizada; aceita arguments ou campos diretos do planner."""
    try:
        if not isinstance(tool_name, str) or tool_name not in REA_MCP_READ_ONLY_TOOLS:
            return {
                "status": "erro",
                "result": "Ferramenta MCP nao autorizada; consulte rea_mcp_list_tools e use apenas a allowlist de leitura.",
            }
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return {"status": "erro", "result": "arguments precisa ser um objeto JSON."}
        arguments = dict(arguments)
        if direct_arguments:
            conflicts = set(arguments).intersection(direct_arguments)
            if conflicts:
                return {
                    "status": "erro",
                    "result": "Argumentos duplicados entre arguments e campos diretos: " + ", ".join(sorted(conflicts)),
                }
            # The planner sometimes flattens a tool's argument fields instead of
            # nesting them under `arguments`; normalize both forms identically.
            arguments.update(direct_arguments)
        open_target = None
        if tool_name == "open_binary":
            target = arguments.get("path")
            if not isinstance(target, str) or not target.strip():
                return {"status": "erro", "result": "path e obrigatorio para abrir um alvo binario REA."}
            path = Path(target).expanduser().resolve(strict=True)
            if not path.is_file():
                return {"status": "erro", "result": "path precisa apontar para um arquivo existente."}
            if not any(path == root or root in path.parents for root in _allowed_roots()):
                return {"status": "erro", "result": "Alvo REA fora das raizes autorizadas em MYRA_REA_ALLOWED_ROOTS."}
            arguments["path"] = str(path)
        elif tool_name in {"current_document", "current_address", "current_procedure", "address_name", "comment", "inline_comment", "inspect_native_instruction", "inspect_native_data_type", "inspect_native_load_image", "resolve_native_call_targets"}:
            try:
                saved = json.loads(ACTIVE_TARGET_FILE.read_text(encoding="utf-8"))
                candidate = saved.get("path") if isinstance(saved, dict) else None
                if isinstance(candidate, str):
                    resolved = Path(candidate).resolve(strict=True)
                    if resolved.is_file() and any(resolved == root or root in resolved.parents for root in _allowed_roots()):
                        open_target = str(resolved)
            except (OSError, ValueError, TypeError):
                open_target = None
        if tool_name == "analyze_javascript_application":
            target = arguments.get("input_path")
            if not isinstance(target, str) or not target.strip():
                return {"status": "erro", "result": "input_path e obrigatorio para analisar uma aplicacao JavaScript."}
            path = Path(target).expanduser().resolve(strict=True)
            if not any(path == root or root in path.parents for root in _allowed_roots()):
                return {"status": "erro", "result": "Alvo MCP fora das raizes autorizadas em MYRA_REA_ALLOWED_ROOTS."}
            if not (path.is_file() or path.is_dir()):
                return {"status": "erro", "result": "input_path precisa ser arquivo ou pasta existente."}
            arguments["input_path"] = str(path)
        elif tool_name in {"inspect_binary_layout", "inspect_go_binary", "inspect_rust_binary"}:
            target = arguments.get("path")
            if not isinstance(target, str) or not target.strip():
                return {"status": "erro", "result": "path e obrigatorio para inspecionar um binario local."}
            path = Path(target).expanduser().resolve(strict=True)
            if not path.is_file():
                return {"status": "erro", "result": "path precisa apontar para um arquivo existente."}
            if not any(path == root or root in path.parents for root in _allowed_roots()):
                return {"status": "erro", "result": "Binario MCP fora das raizes autorizadas em MYRA_REA_ALLOWED_ROOTS."}
            arguments["path"] = str(path)
        encoded = json.dumps(arguments, ensure_ascii=False)
        if len(encoded) > 16_000:
            return {"status": "erro", "result": "Argumentos excedem o limite de 16000 caracteres."}
        request_payload = {"name": tool_name, "arguments": arguments}
        if open_target:
            request_payload["openTarget"] = open_target
        if tool_name in REA_MCP_LONG_RUNNING_TOOLS:
            request_payload["timeoutMs"] = MCP_LONG_TIMEOUT_MS
        payload = _run_mcp_bridge("call", request_payload)
        result = payload.get("result")
        if tool_name == "open_binary" and payload.get("status") == "ok":
            ACTIVE_TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
            ACTIVE_TARGET_FILE.write_text(json.dumps({"path": arguments["path"]}, ensure_ascii=False), encoding="utf-8")
        content = result.get("content") if isinstance(result, dict) else None
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            serialized = "\\n".join(text_parts) if text_parts else json.dumps(result, ensure_ascii=False)
        else:
            serialized = json.dumps(result, ensure_ascii=False)
        return {
            "status": "ok",
            "tool": tool_name,
            "result": serialized[:MAX_OUTPUT_CHARS],
            "truncated": len(serialized) > MAX_OUTPUT_CHARS,
        }
    except subprocess.TimeoutExpired:
        return {"status": "erro", "result": f"A chamada MCP excedeu {MCP_TIMEOUT_SECONDS} segundos."}
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
        "rea_mcp_list_tools",
        rea_mcp_list_tools,
        "Descobre as ferramentas MCP reais do REA e retorna esquemas somente para a allowlist de leitura; nao executa ferramentas."
    )
    registrar_ferramenta(
        "rea_mcp_call",
        rea_mcp_call,
        "Executa ferramentas REA somente pela allowlist de leitura (JS, open_binary, layout, Go/Rust, cursor, endereco, comentarios e instrucoes nativas). Aceita arguments como objeto JSON ou campos diretos do planner. Caminhos devem estar em MYRA_REA_ALLOWED_ROOTS."
    )
    registrar_ferramenta(
        "rea_catalog",
        rea_catalog,
        "Lista os comandos e descricoes publicados pelo catalogo JSON do REA instalado/configurado; nao executa comandos de analise."
    )
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
