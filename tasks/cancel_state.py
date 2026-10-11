# -*- coding: utf-8 -*-
"""Estado global de cancelamento de tasks. Compartilhado entre agent.py e simple_task.py."""

_cancelada = False


def marcar_cancelada() -> None:
    global _cancelada
    _cancelada = True


def resetar() -> None:
    global _cancelada
    _cancelada = False


def esta_cancelada() -> bool:
    return _cancelada
