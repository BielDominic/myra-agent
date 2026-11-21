"""DPAPI-backed local credential vault for MYRA (Windows user scope).

Secrets are encrypted before they touch disk and are never returned by HTTP list APIs.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["credential-vault"])
ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MYRA" / "vault"
VAULT_FILE = ROOT / "credentials.dpapi"
_LOCK = threading.RLock()
_SERVICE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _dpapi():
    if os.name != "nt":
        raise RuntimeError("O cofre DPAPI está disponível nesta versão somente no Windows.")
    try:
        import win32crypt
    except Exception as exc:
        raise RuntimeError("O módulo Windows DPAPI (pywin32) não está disponível.") from exc
    return win32crypt


def _read_store() -> dict[str, Any]:
    if not VAULT_FILE.exists():
        return {"version": 1, "credentials": {}}
    raw = VAULT_FILE.read_bytes()
    if not raw:
        raise RuntimeError("O arquivo do cofre está vazio; nenhum segredo foi alterado.")
    _, clear = _dpapi().CryptUnprotectData(raw, None, None, None, 0)
    data = json.loads(clear.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("credentials"), dict):
        raise RuntimeError("Formato do cofre inválido.")
    return data


def _write_store(data: dict[str, Any]) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = _dpapi().CryptProtectData(payload, "MYRA Credential Vault", None, None, None, 0)
    fd, temp_name = tempfile.mkstemp(prefix=".credentials-", suffix=".tmp", dir=str(ROOT))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encrypted)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, VAULT_FILE)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _validate_service(service: str) -> str:
    value = str(service or "").strip().lower()
    if not _SERVICE_RE.fullmatch(value):
        raise HTTPException(422, "Identificador de serviço inválido.")
    return value


def list_credentials() -> list[dict[str, Any]]:
    with _LOCK:
        try:
            entries = _read_store()["credentials"]
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(503, f"Não foi possível abrir o cofre local: {exc}") from exc
    return [
        {"service": service, "label": item.get("label", service),
         "username": item.get("username", ""), "updated_at": item.get("updated_at", ""),
         "has_secret": bool(item.get("secret"))}
        for service, item in sorted(entries.items())
    ]


def get_credential(service: str) -> dict[str, str] | None:
    """Internal-only secret accessor for trusted backend adapters."""
    service = _validate_service(service)
    with _LOCK:
        try:
            item = _read_store()["credentials"].get(service)
        except FileNotFoundError:
            return None
        except Exception:
            return None
    if not isinstance(item, dict):
        return None
    return {"service": service, "label": str(item.get("label", service)),
            "username": str(item.get("username", "")), "secret": str(item.get("secret", ""))}


class CredentialInput(BaseModel):
    service: str = Field(min_length=1, max_length=64)
    label: str = Field(default="", max_length=100)
    username: str = Field(default="", max_length=254)
    secret: str = Field(min_length=1, max_length=8192)


@router.get("/credentials")
def credentials_list():
    return {"credentials": list_credentials(), "storage": "windows-dpapi-user-scope"}


@router.put("/credentials")
def credentials_save(body: CredentialInput):
    service = _validate_service(body.service)
    if not body.secret.strip():
        raise HTTPException(422, "Informe um segredo antes de salvar.")
    with _LOCK:
        try:
            data = _read_store()
            data.setdefault("credentials", {})[service] = {
                "label": body.label.strip() or service,
                "username": body.username.strip(),
                "secret": body.secret,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_store(data)
        except Exception as exc:
            raise HTTPException(503, f"Não foi possível salvar no cofre DPAPI: {exc}") from exc
    return {"saved": True, "service": service, "has_secret": True}


@router.delete("/credentials/{service}")
def credentials_delete(service: str):
    service = _validate_service(service)
    with _LOCK:
        try:
            data = _read_store()
            if service not in data.get("credentials", {}):
                raise HTTPException(404, "Credencial não encontrada.")
            del data["credentials"][service]
            _write_store(data)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(503, f"Não foi possível atualizar o cofre DPAPI: {exc}") from exc
    return {"deleted": True, "service": service}
