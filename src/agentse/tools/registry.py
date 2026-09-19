from __future__ import annotations

import ast
import operator
from pathlib import Path
from typing import Any, Callable

from agentse.config import Settings, get_settings
from agentse.memory.store import HierarchicalMemory
from agentse.observability.metrics import TOOL_CALLS
from agentse.tools.sandbox import SandboxDenied, run_sandbox

SkillDoc = dict[str, Any]


class ToolRegistry:
    def __init__(self, settings: Settings | None = None, memory: HierarchicalMemory | None = None) -> None:
        self.settings = settings or get_settings()
        self.memory = memory or HierarchicalMemory(self.settings)
        self.fns: dict[str, Callable[..., Any]] = {
            "memory_search": self.memory_search,
            "memory_write": self.memory_write,
            "memory_get": self.memory_get,
            "graph_neighbors": self.graph_neighbors,
            "skill_load": self.skill_load,
            "workspace_read": self.workspace_read,
            "workspace_write": self.workspace_write,
            "sandbox_exec": self.sandbox_exec,
            "calculate": self.calculate,
        }

    def call(self, tool: str, **kwargs: Any) -> Any:
        if tool not in self.fns:
            TOOL_CALLS.labels(tool=tool, status="unknown").inc()
            raise KeyError(tool)
        try:
            result = self.fns[tool](**kwargs)
            TOOL_CALLS.labels(tool=tool, status="ok").inc()
            return result
        except Exception:
            TOOL_CALLS.labels(tool=tool, status="error").inc()
            raise

    def memory_search(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        hits = self.memory.search(query, limit=limit)
        return [{"layer": h.layer, "text": h.text, "score": round(h.score, 4), "meta": h.meta} for h in hits]

    def memory_write(self, fact: str, session_id: str = "default", kind: str = "fact") -> str:
        self.memory.write_episodic(session_id, kind, fact)
        if kind in {"fact", "decision", "preference"}:
            self.memory.remember_fact(fact)
        return "ok"

    def memory_get(self, path: str) -> str:
        resolved = self._safe_workspace(path)
        if not resolved.exists():
            return ""
        return resolved.read_text(encoding="utf-8")[:6000]

    def graph_neighbors(self, name: str) -> list[str]:
        return self.memory.graph_neighbors(name)

    def skill_load(self, name: str) -> str:
        root = Path(__file__).resolve().parents[3] / "skills" / name / "SKILL.md"
        if not root.exists():
            return f"skill {name} not found"
        return root.read_text(encoding="utf-8")[:5000]

    def workspace_read(self, path: str) -> str:
        return self.memory_get(path)

    def workspace_write(self, path: str, content: str) -> str:
        resolved = self._safe_workspace(path)
        if resolved.name in {"SOUL.md", "IDENTITY.md"} and resolved.parent == self.settings.workspace:
            raise PermissionError("SOUL.md и IDENTITY.md только через явный curator-процесс")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return "ok"

    def sandbox_exec(self, code: str) -> dict[str, Any]:
        try:
            return run_sandbox(code, self.settings)
        except SandboxDenied as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc), "exit_code": 403}

    def calculate(self, expression: str) -> float | str:
        allowed = {
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Pow,
            ast.Mod,
            ast.FloorDiv,
            ast.USub,
            ast.UAdd,
        }
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.FloorDiv: operator.floordiv,
        }
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if type(node) not in allowed:
                raise ValueError("expression not allowed")

        def ev(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return ev(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return float(node.value)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                return -ev(node.operand)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
                return ev(node.operand)
            if isinstance(node, ast.BinOp) and type(node.op) in ops:
                return ops[type(node.op)](ev(node.left), ev(node.right))
            raise ValueError("expression not allowed")

        return ev(tree)

    def _safe_workspace(self, path: str) -> Path:
        root = self.settings.workspace.resolve()
        resolved = (root / path).resolve()
        if not str(resolved).startswith(str(root)):
            raise PermissionError("path escapes workspace")
        return resolved

    def catalog(self) -> list[dict[str, str]]:
        return [
            {"name": "memory_search", "args": "query, limit?", "why": "гибридный поиск по слоям памяти"},
            {"name": "memory_write", "args": "fact, session_id?, kind?", "why": "записать факт/эпизод"},
            {"name": "memory_get", "args": "path", "why": "прочитать workspace markdown"},
            {"name": "graph_neighbors", "args": "name", "why": "соседи сущности в графе"},
            {"name": "skill_load", "args": "name", "why": "загрузить процедурный скилл"},
            {"name": "workspace_read", "args": "path", "why": "чтение файла workspace"},
            {"name": "workspace_write", "args": "path, content", "why": "запись в workspace кроме soul"},
            {"name": "sandbox_exec", "args": "code", "why": "исполнить Python в песочнице"},
            {"name": "calculate", "args": "expression", "why": "безопасная арифметика"},
        ]


def default_registry(settings: Settings | None = None) -> ToolRegistry:
    return ToolRegistry(settings)
