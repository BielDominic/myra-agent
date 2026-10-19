"""Autenticacao bearer para os endpoints remotos dedicados da MYRA."""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException


def validar_token_remoto(authorization: str | None) -> bool:
    """Valida token remoto sem aceitar segredo por query string ou registrar seu valor."""
    expected = os.getenv("MYRA_REMOTE_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="API remota desativada: configure MYRA_REMOTE_API_TOKEN.",
        )

    scheme, separator, supplied = (authorization or "").partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not supplied.strip()
        or not hmac.compare_digest(supplied.strip(), expected)
    ):
        raise HTTPException(status_code=401, detail="Token remoto ausente ou invalido.")
    return True
