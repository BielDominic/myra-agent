# -*- coding: utf-8 -*-
"""Configuracao partilhada da consola (Windows cp1252 -> UTF-8).

A consola do Windows costuma usar cp1252. Qualquer ``print`` com texto vindo do
utilizador, do OCR, de paginas web ou de modelos (emojis, ``①``, cirilico, etc.)
levantava ``UnicodeEncodeError`` e derrubava a operacao — nas rotas do
``agent.py`` isso significava HTTP 500.

Importar este modulo aplica a correcao (side-effect), por isso os modulos que
imprimem texto nao controlado devem fazer ``from tasks import console`` no topo.

Se o stream nao suportar ``reconfigure`` (ex.: redireccionado para um objeto
sem essa API), a correcao e ignorada em silencio: nunca deve derrubar nada.
"""
from __future__ import annotations

import sys

_APLICADO = False


def configurar() -> bool:
    """Forca UTF-8 com substituicao em stdout/stderr. Idempotente."""
    global _APLICADO
    if _APLICADO:
        return True
    for nome in ("stdout", "stderr"):
        stream = getattr(sys, nome, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Stream sem reconfigure (ou ja fechado): nao ha nada a fazer.
            pass
    _APLICADO = True
    return True


def imprimir_seguro(texto: str) -> None:
    """Escreve em stdout sem nunca falhar por encoding."""
    configurar()
    try:
        print(texto)
    except Exception:
        try:
            sys.stdout.write(str(texto).encode("utf-8", "replace").decode("utf-8", "replace") + "\n")
        except Exception:
            pass


# Aplica no import: `from tasks import console` ja corrige a consola.
configurar()
