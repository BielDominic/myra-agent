"""Filesystem path containment helpers for MYRA workspace boundaries."""
from pathlib import Path


def path_within_workspace(path: str, workspace: str) -> bool:
    """Return True only if the resolved path is the workspace or inside it.

    Resolving existing symlinks prevents a path inside the workspace from
    escaping through a symlink. Callers should still avoid concurrent
    untrusted filesystem mutation between validation and use (TOCTOU).
    """
    try:
        candidate = Path(path).resolve(strict=False)
        root = Path(workspace).resolve(strict=False)
        return candidate == root or root in candidate.parents
    except (OSError, RuntimeError, ValueError):
        return False
