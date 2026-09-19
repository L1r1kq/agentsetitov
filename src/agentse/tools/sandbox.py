from __future__ import annotations

import ast
import subprocess
from typing import Any

import httpx

from agentse.config import Settings, get_settings
from agentse.observability.metrics import SANDBOX_DENIES, TOOL_CALLS

FORBIDDEN = (
    "import os",
    "import sys",
    "import socket",
    "import subprocess",
    "import pathlib",
    "from os",
    "from sys",
    "from socket",
    "from subprocess",
    "open(",
    "__import__",
    "eval(",
    "exec(",
    "compile(",
    "input(",
    "breakpoint(",
)


class SandboxDenied(RuntimeError):
    pass


def _static_guard(code: str) -> None:
    lowered = code.lower()
    for token in FORBIDDEN:
        if token in lowered:
            SANDBOX_DENIES.labels(reason="static").inc()
            raise SandboxDenied(f"запрещённый примитив: {token}")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        SANDBOX_DENIES.labels(reason="syntax").inc()
        raise SandboxDenied(f"синтаксис: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            SANDBOX_DENIES.labels(reason="import").inc()
            raise SandboxDenied("import запрещён в песочнице")
        if isinstance(node, ast.Attribute) and isinstance(node.attr, str):
            if node.attr.startswith("__"):
                SANDBOX_DENIES.labels(reason="dunder").inc()
                raise SandboxDenied("dunder-атрибуты запрещены")


def run_sandbox(code: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    _static_guard(code)
    if settings.sandbox_enabled:
        try:
            response = httpx.post(
                f"{settings.sandbox_url.rstrip('/')}/exec",
                json={"code": code},
                timeout=settings.sandbox_timeout_s,
            )
            response.raise_for_status()
            TOOL_CALLS.labels(tool="sandbox_exec", status="ok").inc()
            return response.json()
        except (httpx.HTTPError, OSError):
            # Локальный fallback: тот же контракт, но процесс на хосте с лимитами.
            pass
    return _local_restricted(code, settings)


def _local_restricted(code: str, settings: Settings) -> dict[str, Any]:
    script = (
        "import math, statistics, json, sys\n"
        f"code = {code!r}\n"
        "ns = {'math': math, 'statistics': statistics, 'json': json}\n"
        "try:\n"
        "    exec(compile(code, '<sandbox>', 'exec'), ns, ns)\n"
        "    out = ns.get('result', ns.get('answer'))\n"
        "    print(out if out is not None else '')\n"
        "except Exception as e:\n"
        "    print('ERR', type(e).__name__, e, file=sys.stderr)\n"
        "    sys.exit(2)\n"
    )
    try:
        proc = subprocess.run(
            ["python3", "-c", script],
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        SANDBOX_DENIES.labels(reason="timeout").inc()
        TOOL_CALLS.labels(tool="sandbox_exec", status="timeout").inc()
        return {"ok": False, "stdout": "", "stderr": "timeout", "exit_code": 124}
    status = "ok" if proc.returncode == 0 else "error"
    TOOL_CALLS.labels(tool="sandbox_exec", status=status).inc()
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
        "exit_code": proc.returncode,
        "mode": "local-restricted",
    }
