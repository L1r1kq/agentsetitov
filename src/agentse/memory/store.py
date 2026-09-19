from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from agentse.config import Settings, get_settings
from agentse.observability.metrics import MEMORY_HITS, MEMORY_WRITES

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_]{2,}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def lexical_score(query: str, text: str) -> float:
    q = set(tokenize(query))
    if not q:
        return 0.0
    t = set(tokenize(text))
    overlap = len(q & t)
    return overlap / math.sqrt(len(q) * max(len(t), 1))


@dataclass
class MemoryHit:
    layer: str
    text: str
    score: float
    meta: dict[str, Any]


class HierarchicalMemory:
    """Иерархическая память: identity + episodic + semantic graph + daily notes.

    Это не RAG. RAG — одноразовый retrieval чанков. Здесь есть запись,
    консолидация, граф сущностей, затухание и слои с разным контрактом.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self.conn = sqlite3.connect(self.settings.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                session_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
                content, session_id, kind, content='episodic', content_rowid='id'
            );
            CREATE TRIGGER IF NOT EXISTS episodic_ai AFTER INSERT ON episodic BEGIN
                INSERT INTO episodic_fts(rowid, content, session_id, kind)
                VALUES (new.id, new.content, new.session_id, new.kind);
            END;
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                etype TEXT NOT NULL,
                attrs TEXT NOT NULL DEFAULT '{}',
                strength REAL NOT NULL DEFAULT 1.0,
                last_seen TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src TEXT NOT NULL,
                rel TEXT NOT NULL,
                dst TEXT NOT NULL,
                evidence TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                ts TEXT NOT NULL,
                UNIQUE(src, rel, dst)
            );
            """
        )
        self.conn.commit()

    def write_episodic(self, session_id: str, kind: str, content: str) -> None:
        ts = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO episodic(ts, session_id, kind, content) VALUES (?, ?, ?, ?)",
            (ts, session_id, kind, content),
        )
        self.conn.commit()
        MEMORY_WRITES.labels(layer="episodic").inc()
        self._append_daily(f"- [{kind}] {content.strip()}\n")

    def remember_fact(self, fact: str, entities: Iterable[tuple[str, str]] | None = None) -> None:
        path = self.settings.workspace / "MEMORY.md"
        stamp = datetime.now(UTC).date().isoformat()
        block = f"\n- ({stamp}) {fact.strip()}\n"
        if path.exists():
            current = path.read_text(encoding="utf-8")
            if fact.strip() in current:
                return
        else:
            current = "# MEMORY\n\nКураторские факты. Не транскрипт.\n"
        path.write_text(current + block, encoding="utf-8")
        MEMORY_WRITES.labels(layer="semantic").inc()
        for name, etype in entities or ():
            self.upsert_entity(name, etype)

    def upsert_entity(self, name: str, etype: str, attrs: dict[str, Any] | None = None) -> None:
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            """
            INSERT INTO entities(name, etype, attrs, strength, last_seen)
            VALUES (?, ?, ?, 1.0, ?)
            ON CONFLICT(name) DO UPDATE SET
                strength = MIN(entities.strength + 0.25, 5.0),
                last_seen = excluded.last_seen,
                etype = excluded.etype
            """,
            (name.lower(), etype, json.dumps(attrs or {}, ensure_ascii=False), now),
        )
        self.conn.commit()
        MEMORY_WRITES.labels(layer="graph").inc()

    def relate(self, src: str, rel: str, dst: str, evidence: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.conn.execute(
            """
            INSERT INTO relations(src, rel, dst, evidence, weight, ts)
            VALUES (?, ?, ?, ?, 1.0, ?)
            ON CONFLICT(src, rel, dst) DO UPDATE SET
                weight = MIN(relations.weight + 0.2, 5.0),
                evidence = excluded.evidence,
                ts = excluded.ts
            """,
            (src.lower(), rel, dst.lower(), evidence, now),
        )
        self.conn.commit()

    def decay(self) -> None:
        self.conn.execute(
            "UPDATE entities SET strength = strength * ?",
            (self.settings.memory_decay,),
        )
        self.conn.execute(
            "UPDATE relations SET weight = weight * ?",
            (self.settings.memory_decay,),
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 6) -> list[MemoryHit]:
        hits: list[MemoryHit] = []
        hits.extend(self._search_identity(query))
        hits.extend(self._search_episodic(query, limit=limit))
        hits.extend(self._search_graph(query))
        hits.sort(key=lambda h: h.score, reverse=True)
        for hit in hits[:limit]:
            MEMORY_HITS.labels(layer=hit.layer).inc()
        return hits[:limit]

    def _search_identity(self, query: str) -> list[MemoryHit]:
        hits: list[MemoryHit] = []
        for name in ("MEMORY.md", "USER.md", "AGENTS.md"):
            path = self.settings.workspace / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            score = lexical_score(query, text)
            if score > 0:
                snippet = self._best_snippet(query, text)
                hits.append(MemoryHit("identity", snippet, score + 0.15, {"file": name}))
        daily = self.settings.workspace / "memory"
        if daily.exists():
            for path in sorted(daily.glob("*.md"))[-3:]:
                text = path.read_text(encoding="utf-8")
                score = lexical_score(query, text)
                if score > 0:
                    hits.append(
                        MemoryHit(
                            "episodic-md",
                            self._best_snippet(query, text),
                            score,
                            {"file": str(path.name)},
                        )
                    )
        return hits

    def _search_episodic(self, query: str, limit: int) -> list[MemoryHit]:
        hits: list[MemoryHit] = []
        try:
            rows = self.conn.execute(
                "SELECT content, kind, session_id FROM episodic_fts WHERE episodic_fts MATCH ? LIMIT ?",
                (query.replace('"', " "), limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = self.conn.execute(
                "SELECT content, kind, session_id FROM episodic ORDER BY id DESC LIMIT ?",
                (limit * 3,),
            ).fetchall()
        for row in rows:
            score = lexical_score(query, row["content"])
            hits.append(
                MemoryHit(
                    "episodic",
                    row["content"][:400],
                    score,
                    {"kind": row["kind"], "session_id": row["session_id"]},
                )
            )
        return hits

    def _search_graph(self, query: str) -> list[MemoryHit]:
        tokens = tokenize(query)
        if not tokens:
            return []
        placeholders = ",".join("?" for _ in tokens)
        entities = self.conn.execute(
            f"SELECT name, etype, strength FROM entities WHERE name IN ({placeholders})",
            tokens,
        ).fetchall()
        hits: list[MemoryHit] = []
        for ent in entities:
            rels = self.conn.execute(
                "SELECT src, rel, dst, evidence, weight FROM relations WHERE src = ? OR dst = ? ORDER BY weight DESC LIMIT 5",
                (ent["name"], ent["name"]),
            ).fetchall()
            for rel in rels:
                text = f"{rel['src']} -{rel['rel']}-> {rel['dst']}: {rel['evidence']}"
                hits.append(
                    MemoryHit(
                        "graph",
                        text,
                        0.4 + 0.1 * float(rel["weight"]) + 0.05 * float(ent["strength"]),
                        {"entity": ent["name"]},
                    )
                )
        return hits

    def graph_neighbors(self, name: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT src, rel, dst, evidence FROM relations WHERE src = ? OR dst = ?",
            (name.lower(), name.lower()),
        ).fetchall()
        return [f"{r['src']} -{r['rel']}-> {r['dst']}: {r['evidence']}" for r in rows]

    def _append_daily(self, line: str) -> None:
        day = datetime.now(UTC).date().isoformat()
        path = self.settings.workspace / "memory" / f"{day}.md"
        if not path.exists():
            path.write_text(f"# {day}\n\nЭпизодические заметки дня.\n\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    @staticmethod
    def _best_snippet(query: str, text: str, window: int = 280) -> str:
        q = tokenize(query)
        lower = text.lower()
        best_i = 0
        best = 0
        for token in q:
            i = lower.find(token)
            if i >= 0:
                score = lower.count(token)
                if score > best:
                    best = score
                    best_i = i
        start = max(0, best_i - 80)
        return text[start : start + window].strip()

    def close(self) -> None:
        self.conn.close()
