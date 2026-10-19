"""Diagnostico local do Tailscale sem alterar rede ou firewall.

A ferramenta so le o estado do cliente local. Ela nao faz login, nao expoe a API
FastAPI e nao publica servicos no tailnet automaticamente.
"""
from __future__ import annotations

import ipaddress
import json
import os
import shutil
import subprocess
from pathlib import Path


def _find_tailscale() -> str | None:
    found = shutil.which("tailscale") or shutil.which("tailscale.exe")
    if found:
        return found
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidate = program_files / "Tailscale" / "tailscale.exe"
    return str(candidate) if candidate.is_file() else None


def tailscale_status() -> dict:
    """Retorna somente dados do proprio dispositivo; nunca lista peers do tailnet."""
    executable = _find_tailscale()
    if not executable:
        return {
            "status": "not_installed",
            "installed": False,
            "connected": False,
            "tailscale_ip": None,
            "device_name": None,
            "message": "Tailscale nao encontrado. Instale o cliente oficial e entre na mesma conta no PC e no iPhone.",
            "api_exposed": False,
        }

    try:
        completed = subprocess.run(
            [executable, "status", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "installed": True,
            "connected": False,
            "tailscale_ip": None,
            "device_name": None,
            "message": "O cliente Tailscale nao respondeu em 8 segundos.",
            "api_exposed": False,
        }
    except OSError as exc:
        return {
            "status": "error",
            "installed": True,
            "connected": False,
            "tailscale_ip": None,
            "device_name": None,
            "message": f"Nao foi possivel consultar o Tailscale ({type(exc).__name__}).",
            "api_exposed": False,
        }

    if completed.returncode != 0:
        return {
            "status": "not_ready",
            "installed": True,
            "connected": False,
            "tailscale_ip": None,
            "device_name": None,
            "message": "O Tailscale esta instalado, mas nao informou um estado conectado. Abra o cliente e conclua o login.",
            "api_exposed": False,
        }

    try:
        data = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "status": "invalid_response",
            "installed": True,
            "connected": False,
            "tailscale_ip": None,
            "device_name": None,
            "message": "O Tailscale retornou um estado que nao pode ser interpretado.",
            "api_exposed": False,
        }

    self_data = data.get("Self") or {}
    ips = self_data.get("TailscaleIPs") or []
    valid_ip = None
    network = ipaddress.ip_network("100.64.0.0/10")
    for raw_ip in ips:
        try:
            parsed = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if parsed.version == 4 and parsed in network:
            valid_ip = str(parsed)
            break

    backend_state = str(data.get("BackendState") or "Unknown")
    connected = backend_state.lower() == "running" and bool(valid_ip)
    if connected:
        message = "Tailscale conectado. A API da MYRA continua local e nao foi exposta ao tailnet."
        status = "connected"
    elif backend_state.lower() == "needslogin":
        message = "Tailscale instalado; falta entrar na conta no PC."
        status = "needs_login"
    else:
        message = f"Tailscale instalado, estado: {backend_state}. A API da MYRA nao foi exposta."
        status = "not_connected"

    return {
        "status": status,
        "installed": True,
        "connected": connected,
        "tailscale_ip": valid_ip if connected else None,
        "device_name": str(self_data.get("HostName") or "") or None,
        "backend_state": backend_state,
        "message": message,
        "api_exposed": False,
    }
