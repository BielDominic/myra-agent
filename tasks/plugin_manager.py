"""Secure, declarative MYRA plugin package intake.

Only Markdown/text Skills and Prompts are accepted here. Third-party executable
code is never imported or executed by the FastAPI process.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["plugins"])

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_FILES = 500
MAX_MANIFEST_BYTES = 64 * 1024
MAX_INSTRUCTION_BYTES = 256 * 1024
PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+){1,7}$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
ALLOWED_TYPES = {"skill", "prompt"}
ALLOWED_SUFFIXES = {".md", ".txt", ".json"}
REGISTRY_VERSION = 1


def plugin_root() -> Path:
    override = os.environ.get("MYRA_PLUGIN_DIR")
    if override:
        root = Path(override).expanduser()
    else:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = (Path(base) / "MYRA" / "plugins") if base else (Path.home() / ".myra" / "plugins")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _registry_path() -> Path:
    return plugin_root() / "registry.json"


def _read_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.exists():
        return {"schema_version": REGISTRY_VERSION, "plugins": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(500, "Registro de plugins inválido; preserve o arquivo para recuperação.")
    if not isinstance(data, dict) or data.get("schema_version") != REGISTRY_VERSION or not isinstance(data.get("plugins"), list):
        raise HTTPException(500, "Versão ou formato do registro de plugins não suportado.")
    return data


def _write_registry(data: dict[str, Any]) -> None:
    path = _registry_path()
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _safe_member_name(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\x00" in raw or chr(92) in raw:
        raise ValueError("Caminho inválido no pacote.")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("O pacote contém caminho absoluto ou traversal.")
    normalized = path.as_posix()
    if normalized.startswith("/") or ":" in path.parts[0]:
        raise ValueError("O pacote contém caminho não permitido.")
    if path.suffix.lower() not in ALLOWED_SUFFIXES and normalized != "LICENSE":
        raise ValueError("Pacotes declarativos aceitam apenas arquivos Markdown, texto e JSON.")
    return normalized


def validate_archive(payload: bytes) -> tuple[dict[str, Any], list[tuple[str, bytes]], str]:
    if not payload or len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP vazio ou acima do limite de 20 MB.")
    digest = hashlib.sha256(payload).hexdigest()
    try:
        archive = zipfile.ZipFile(__import__("io").BytesIO(payload))
    except (zipfile.BadZipFile, OSError):
        raise ValueError("O arquivo enviado não é um ZIP válido.") from None

    members: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    total = 0
    with archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_FILES:
            raise ValueError("Quantidade de arquivos inválida no pacote.")
        for info in infos:
            if info.is_dir():
                continue
            name = _safe_member_name(info.filename)
            if name in seen:
                raise ValueError("O pacote contém caminhos duplicados.")
            seen.add(name)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError("Links simbólicos não são permitidos.")
            if info.flag_bits & 0x1:
                raise ValueError("Arquivos ZIP criptografados não são aceitos.")
            if info.file_size < 0 or info.file_size > MAX_UNPACKED_BYTES:
                raise ValueError("Arquivo individual acima do limite permitido.")
            total += info.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("Conteúdo descompactado acima de 50 MB.")
            data = archive.read(info)
            if len(data) != info.file_size:
                raise ValueError("Tamanho do arquivo ZIP inconsistente.")
            members.append((name, data))

    by_name = dict(members)
    manifest_raw = by_name.get("myra.plugin.json")
    if manifest_raw is None or len(manifest_raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Pacote precisa conter myra.plugin.json (máximo 64 KB).")
    try:
        manifest = json.loads(manifest_raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Manifesto JSON inválido ou não UTF-8.") from None
    if not isinstance(manifest, dict):
        raise ValueError("O manifesto precisa ser um objeto JSON.")

    required = ("id", "version", "name", "description", "type", "entry_point")
    missing = [key for key in required if not isinstance(manifest.get(key), str) or not manifest[key].strip()]
    if missing:
        raise ValueError("Campos obrigatórios ausentes: " + ", ".join(missing))
    plugin_id = manifest["id"].strip()
    version = manifest["version"].strip()
    if not PLUGIN_ID_RE.fullmatch(plugin_id):
        raise ValueError("ID inválido; use minúsculas, números, ponto ou hífen.")
    if not SEMVER_RE.fullmatch(version):
        raise ValueError("Versão precisa seguir Semantic Versioning.")
    if manifest["type"] not in ALLOWED_TYPES:
        raise ValueError("Por segurança, apenas plugins declarativos do tipo skill ou prompt são aceitos.")
    if len(manifest["name"]) > 100 or len(manifest["description"]) > 1000:
        raise ValueError("Nome ou descrição excede o limite.")
    if manifest.get("capabilities", []) not in ([], None) or manifest.get("permissions", []) not in ([], None):
        raise ValueError("Skills e Prompts declarativos não podem solicitar permissões ou capacidades.")
    entry = _safe_member_name(manifest["entry_point"])
    if Path(entry).suffix.lower() not in {".md", ".txt"} or entry not in by_name:
        raise ValueError("entry_point precisa apontar para um arquivo .md ou .txt existente.")
    if len(by_name[entry]) > MAX_INSTRUCTION_BYTES:
        raise ValueError("Instruções excedem o limite de 256 KB.")
    if "README.md" not in by_name:
        raise ValueError("Pacote precisa incluir README.md.")
    if "LICENSE" not in by_name and "LICENSE.md" not in by_name and "LICENSE.txt" not in by_name:
        raise ValueError("Pacote precisa incluir um arquivo de licença.")
    # Reject binary/control content: the accepted package format is declarative text only.
    for name, data in members:
        if b"\x00" in data:
            raise ValueError(f"Conteúdo binário não permitido: {name}")
        if name.lower().endswith((".md", ".txt")):
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise ValueError(f"Arquivo de texto não está em UTF-8: {name}") from None
    return manifest, members, digest


def install_archive(payload: bytes) -> dict[str, Any]:
    try:
        manifest, members, digest = validate_archive(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    registry = _read_registry()
    plugin_id, version = manifest["id"], manifest["version"]
    if any(p.get("id") == plugin_id and p.get("version") == version for p in registry["plugins"]):
        raise HTTPException(409, "Esta versão do plugin já está instalada.")

    root = plugin_root()
    target_parent = root / plugin_id
    target = target_parent / version
    if target.exists():
        raise HTTPException(409, "O diretório de destino já existe; nenhuma alteração foi feita.")
    target_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".myra-plugin-", dir=str(root)))
    try:
        for name, data in members:
            destination = (staging / name).resolve()
            destination.relative_to(staging.resolve())
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        target_parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    record = {
        "id": plugin_id,
        "version": version,
        "name": manifest["name"],
        "description": manifest["description"],
        "type": manifest["type"],
        "entry_point": manifest["entry_point"],
        "sha256": digest,
        "installed": True,
        "enabled": False,
        "permissions": [],
        "installed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "path": str(target),
    }
    registry["plugins"].append(record)
    _write_registry(registry)
    return {key: value for key, value in record.items() if key != "path"}


async def _read_archive_body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_ARCHIVE_BYTES:
                raise HTTPException(413, "Pacote excede o limite de 20 MB.")
        except ValueError:
            raise HTTPException(400, "Content-Length inválido.") from None
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > MAX_ARCHIVE_BYTES:
            raise HTTPException(413, "Pacote excede o limite de 20 MB.")
    return bytes(chunks)


def _catalog_path() -> Path:
    return Path(__file__).resolve().parent.parent / "plugins" / "catalog.json"


def get_catalog() -> dict[str, Any]:
    """Return the reviewed, local catalog plus installation state."""
    path = _catalog_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(500, "Catalogo local de plugins indisponivel.") from None
    entries = data.get("catalogue") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise HTTPException(500, "Formato do catalogo de plugins invalido.")
    installed = _read_registry()["plugins"]
    latest = {}
    for item in installed:
        if isinstance(item, dict):
            current = latest.get(item.get("id"))
            if current is None or str(item.get("installed_at", "")) > str(current.get("installed_at", "")):
                latest[item.get("id")] = item
    result = []
    for raw in entries:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            continue
        item = dict(raw)
        local = latest.get(item["id"])
        item["installed"] = bool(local)
        item["enabled"] = bool(local and local.get("enabled"))
        item["installed_version"] = local.get("version") if local else None
        result.append(item)
    return {"schema_version": data.get("schema_version", 1), "plugins": result}


def get_enabled_instructions(max_total_bytes: int = 32768) -> list[dict[str, str]]:
    """Load enabled declarative skills as bounded, untrusted prompt context."""
    root = plugin_root().resolve()
    registry = _read_registry()
    loaded: list[dict[str, str]] = []
    total = 0
    for record in registry["plugins"]:
        if not isinstance(record, dict) or not record.get("enabled") or record.get("type") not in ALLOWED_TYPES:
            continue
        plugin_id, version, entry = record.get("id"), record.get("version"), record.get("entry_point")
        if not all(isinstance(value, str) and value for value in (plugin_id, version, entry)):
            continue
        try:
            safe_entry = _safe_member_name(entry)
            path = (root / plugin_id / version / safe_entry).resolve()
            path.relative_to(root)
            if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
                continue
            remaining = max_total_bytes - total
            if remaining <= 0:
                break
            raw = path.read_bytes()[:remaining]
            content = raw.decode("utf-8-sig", errors="ignore")
        except (OSError, ValueError):
            continue
        if not content.strip():
            continue
        total += len(raw)
        loaded.append({"id": plugin_id, "name": str(record.get("name") or plugin_id), "content": content})
    return loaded


def set_plugin_enabled(plugin_id: str, enabled: bool) -> dict[str, Any]:
    if not PLUGIN_ID_RE.fullmatch(plugin_id):
        raise HTTPException(400, "ID de plugin invalido.")
    registry = _read_registry()
    records = [p for p in registry["plugins"] if p.get("id") == plugin_id]
    if not records:
        raise HTTPException(404, "Plugin nao encontrado.")
    # Enable/disable is a library state only. Declarative content is never
    # imported as Python/JavaScript or granted system capabilities.
    for record in records:
        record["enabled"] = bool(enabled)
    _write_registry(registry)
    return {"id": plugin_id, "enabled": bool(enabled), "versions": len(records), "executable_code": False}


@router.get("/plugins")
def list_plugins():
    return {"schema_version": REGISTRY_VERSION, "plugins": _read_registry()["plugins"]}


@router.post("/plugins/validate")
async def validate_plugin(request: Request):
    payload = await _read_archive_body(request)
    try:
        manifest, members, digest = validate_archive(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return {
        "valid": True,
        "id": manifest["id"],
        "version": manifest["version"],
        "name": manifest["name"],
        "type": manifest["type"],
        "files": len(members),
        "sha256": digest,
        "executable_code": False,
        "enabled_by_default": False,
    }


@router.post("/plugins/install")
async def install_plugin(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {"application/zip", "application/octet-stream"}:
        raise HTTPException(415, "Envie um pacote ZIP com Content-Type application/zip.")
    return install_archive(await _read_archive_body(request))


@router.delete("/plugins/{plugin_id}")
def remove_plugin(plugin_id: str):
    registry = _read_registry()
    records = [p for p in registry["plugins"] if p.get("id") == plugin_id]
    if not records:
        raise HTTPException(404, "Plugin não encontrado.")
    if any(p.get("enabled") for p in records):
        raise HTTPException(409, "Desative o plugin antes de removê-lo.")
    root = plugin_root()
    plugin_dir = (root / plugin_id).resolve()
    try:
        plugin_dir.relative_to(root)
    except ValueError:
        raise HTTPException(400, "Caminho de plugin inválido.") from None
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    registry["plugins"] = [p for p in registry["plugins"] if p.get("id") != plugin_id]
    _write_registry(registry)
    return {"removed": True, "id": plugin_id}


@router.get("/plugins/catalog")
def plugin_catalog():
    return get_catalog()


@router.post("/plugins/{plugin_id}/enable")
def enable_plugin(plugin_id: str):
    return set_plugin_enabled(plugin_id, True)


@router.post("/plugins/{plugin_id}/disable")
def disable_plugin(plugin_id: str):
    return set_plugin_enabled(plugin_id, False)
