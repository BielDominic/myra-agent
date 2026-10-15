# -*- coding: utf-8 -*-
"""Estado global de cancelamento/pausa de tasks.

Compartilhado entre agent.py e simple_task.py. O cancelamento aborta a task;
a pausa apenas interrompe o loop, deixando o estado persistido em
tasks/task_store.py para retomar depois sem perder contexto (FASE 26).
"""

_cancelada = False
_pausada = False


def marcar_cancelada() -> None:
    global _cancelada
    _cancelada = True


def resetar() -> None:
    global _cancelada
    _cancelada = False


def esta_cancelada() -> bool:
    return _cancelada


def marcar_pausada() -> None:
    global _pausada
    _pausada = True


def resetar_pausa() -> None:
    global _pausada
    _pausada = False


def esta_pausada() -> bool:
    return _pausada
