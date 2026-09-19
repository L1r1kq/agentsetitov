from __future__ import annotations

from pathlib import Path

from agentse.config import Settings, get_settings

IDENTITY_FILES = (
    "PURPOSE.md",
    "SOUL.md",
    "IDENTITY.md",
    "AGENTS.md",
    "USER.md",
    "TOOLS.md",
    "MEMORY.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
)

PER_FILE_LIMIT = 8_000
TOTAL_LIMIT = 28_000


def _read_capped(path: Path, limit: int) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if len(text) > limit:
        return text[:limit] + "\n\n[truncated]\n"
    return text


def load_identity(settings: Settings | None = None, extra: list[str] | None = None) -> str:
    settings = settings or get_settings()
    chunks: list[str] = []
    used = 0
    for name in IDENTITY_FILES + tuple(extra or ()):
        text = _read_capped(settings.workspace / name, PER_FILE_LIMIT)
        if not text:
            continue
        block = f"## FILE {name}\n{text.strip()}\n"
        if used + len(block) > TOTAL_LIMIT:
            remain = TOTAL_LIMIT - used
            if remain > 80:
                chunks.append(block[:remain] + "\n[budget exceeded]\n")
            break
        chunks.append(block)
        used += len(block)
    return "\n".join(chunks)


def load_agent_soul(agent: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    path = settings.workspace / "agents" / agent / "SOUL.md"
    return _read_capped(path, PER_FILE_LIMIT)


def today_memory(settings: Settings | None = None) -> str:
    from datetime import UTC, datetime

    settings = settings or get_settings()
    today = datetime.now(UTC).date().isoformat()
    return _read_capped(settings.workspace / "memory" / f"{today}.md", 4_000)
