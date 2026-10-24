"""Descoberta e abertura controlada de aplicativos Windows por nome.

Resolve somente atalhos conhecidos do menu Iniciar/desktop e entradas de
aplicativos instalados. Não executa comandos arbitrários fornecidos pelo planner.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _atalhos_raiz() -> list[Path]:
    bases = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
    ]
    return [p for p in bases if str(p) and p.is_dir()]


def _apps_menu_iniciar() -> list[dict]:
    """Obtém apps registrados no menu Iniciar, incluindo apps MSIX/UWP."""
    if os.name != "nt":
        return []
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=8, check=False,
            encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        dados = json.loads(proc.stdout)
        if isinstance(dados, dict):
            dados = [dados]
        resultado = []
        for item in dados if isinstance(dados, list) else []:
            nome = str(item.get("Name") or "").strip()
            app_id = str(item.get("AppID") or "").strip()
            if nome and app_id and not any(ord(c) < 32 for c in app_id):
                resultado.append({"nome": nome, "atalho": f"shell:AppsFolder\\{app_id}", "origem": "Windows StartApps"})
        return resultado
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return []


def listar_aplicativos() -> dict:
    """Lista atalhos de aplicativos disponíveis nos menus Iniciar e desktops."""
    try:
        encontrados = {}
        for raiz in _atalhos_raiz():
            for p in raiz.rglob("*"):
                try:
                    if p.is_file() and p.suffix.lower() in {".lnk", ".url", ".appref-ms"}:
                        nome = p.stem.strip()
                        if nome:
                            chave = str(p.resolve()).casefold()
                            encontrados[chave] = {"nome": nome, "atalho": str(p), "origem": str(raiz)}
                except (OSError, PermissionError):
                    continue
        # Inclui aplicativos registrados no menu Iniciar, como WhatsApp MSIX/UWP,
        # que podem não possuir um atalho .lnk nos diretórios pesquisados.
        for app in _apps_menu_iniciar():
            chave = f"startapps:{app['atalho'].casefold()}"
            encontrados.setdefault(chave, app)
        apps = sorted(encontrados.values(), key=lambda x: x["nome"].casefold())
        return {"status": "ok", "total": len(apps), "result": apps}
    except Exception as exc:
        return {"status": "erro", "result": f"{type(exc).__name__}: {exc}"}


def abrir_aplicativo(nome: str) -> dict:
    """Abre um atalho conhecido por nome exato ou correspondência inequívoca."""
    nome = (nome or "").strip()
    if not nome or len(nome) > 160 or any(ord(c) < 32 for c in nome):
        return {"status": "erro", "result": "Informe um nome de aplicativo válido (1–160 caracteres)."}
    inventario = listar_aplicativos()
    if inventario.get("status") != "ok":
        return inventario
    apps = inventario["result"]
    consulta = nome.casefold()
    # Aliases PT-BR comuns para aplicativos cujo nome oficial no Windows est? em ingl?s.
    aliases = {
        "bloco de notas": "notepad",
        "notas": "notepad",
        "calculadora": "calculator",
        "gerenciador de tarefas": "task manager",
        "explorador de arquivos": "file explorer",
        "prompt de comando": "command prompt",
    }
    consulta = aliases.get(consulta, consulta)
    exatos = [a for a in apps if a["nome"].casefold() == consulta]
    candidatos = exatos or [a for a in apps if consulta in a["nome"].casefold()]
    if not candidatos:
        return {"status": "erro", "result": f"Nenhum atalho encontrado para {nome!r}. Liste os aplicativos para ver nomes disponíveis."}
    if len(candidatos) > 1:
        return {"status": "ambiguous", "result": [{"nome": a["nome"], "atalho": a["atalho"]} for a in candidatos[:15]], "message": "Há vários aplicativos correspondentes; informe um nome mais específico."}
    alvo = candidatos[0]["atalho"]
    try:
        os.startfile(alvo)  # Windows Shell resolve .lnk/.url sem shell command injection.
        return {"status": "ok", "result": f"Solicitada abertura de {candidatos[0]['nome']}", "nome": candidatos[0]["nome"], "atalho": alvo}
    except OSError as exc:
        return {"status": "erro", "result": f"Falha ao abrir {candidatos[0]['nome']}: {type(exc).__name__}: {exc}"}


def desinstalar_aplicativo(nome: str) -> dict:
    """Desinstala um pacote Appx/MSIX pelo nome, sem aceitar comandos arbitrarios."""
    nome = (nome or "").strip()
    if not nome or len(nome) > 160 or any(ord(c) < 32 for c in nome):
        return {"status": "erro", "result": "Informe um nome de aplicativo valido."}
    if os.name != "nt":
        return {"status": "erro", "result": "Disponivel apenas no Windows."}
    script = "$ErrorActionPreference='Stop'; $n=[Console]::In.ReadToEnd() | ConvertFrom-Json; $name=[string]$n.nome; $key=($name -replace '[^a-zA-Z0-9]','').ToLowerInvariant(); $p=@(Get-AppxPackage | Where-Object { $_.Name -eq $name -or $_.PackageFullName -eq $name }); if ($p.Count -eq 0) { $p=@(Get-AppxPackage | Where-Object { $_.Name -like ('*'+$name+'*') -or (($_.Name -replace '[^a-zA-Z0-9]','').ToLowerInvariant()).Contains($key) }) }; if ($p.Count -eq 0) { @{status='not_found';result='Nenhum pacote correspondente instalado neste perfil.'} | ConvertTo-Json -Compress; exit 0 }; if ($p.Count -ne 1) { @{status='ambiguous';result=@($p | ForEach-Object {$_.Name});message='Informe um nome exato; ha multiplos pacotes.'} | ConvertTo-Json -Compress; exit 0 }; $target=$p[0]; Remove-AppxPackage -Package $target.PackageFullName; $left=@(Get-AppxPackage | Where-Object {$_.Name -eq $target.Name}); if ($left.Count -eq 0) { @{status='ok';result=('Aplicativo '+$target.Name+' removido e verificado.');package=$target.PackageFullName;verified=$true} | ConvertTo-Json -Compress } else { @{status='erro';result='O pacote continua instalado.';verified=$false} | ConvertTo-Json -Compress }"
    try:
        proc=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script], input=json.dumps({"nome":nome}), capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
        lines=proc.stdout.strip().splitlines()
        if proc.returncode != 0 or not lines:
            return {"status":"erro","result":(proc.stderr or proc.stdout or "PowerShell falhou")[-1500:]}
        try: return json.loads(lines[-1])
        except ValueError: return {"status":"erro","result":lines[-1][:1500]}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status":"erro","result":f"{type(exc).__name__}: {exc}"}
