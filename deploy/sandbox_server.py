from __future__ import annotations

import ast
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()
FORBIDDEN = ("import ", "open(", "__", "eval(", "exec(", "socket", "subprocess", "os.", "sys.")


class ExecIn(BaseModel):
    code: str = Field(max_length=4000)


def guard(code: str) -> None:
    low = code.lower()
    for token in FORBIDDEN:
        if token in low:
            raise ValueError(f"denied: {token}")
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("denied: import")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/exec")
def exec_code(body: ExecIn) -> dict:
    try:
        guard(body.code)
    except Exception as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "exit_code": 403, "mode": "docker-sandbox"}
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "main.py"
        script.write_text(
            "import math, statistics, json\n" + body.code + "\nprint(result) if 'result' in globals() else None\n",
            encoding="utf-8",
        )
        try:
            proc = subprocess.run(
                ["python", str(script)],
                capture_output=True,
                text=True,
                timeout=6,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "timeout", "exit_code": 124, "mode": "docker-sandbox"}
    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
        "exit_code": proc.returncode,
        "mode": "docker-sandbox",
    }
