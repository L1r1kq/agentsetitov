from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentse.medical_guard import has_red_flag, strip_diagnosis

EMPTY_MARKERS = {"", "{}", "[]", "{ }", "null", "none", "None"}

TOPIC_CARDS = (
    (("температур", "жар", "кашел", "простуд", "орви"), "fever_cough.md"),
    (("головн", "мигрен"), "headache.md"),
    (("горл", "глота", "перш"), "sore_throat.md"),
    (("живот", "тошнот", "понос", "диаре", "рвот"), "abdominal.md"),
    (("боль в груди", "давящ", "за грудин", "холодн"), "chest_pain.md"),
)

CARD_TITLES = {
    "fever_cough.md": "Жар и кашель",
    "headache.md": "Головная боль",
    "sore_throat.md": "Боль в горле",
    "abdominal.md": "Живот и стул",
    "chest_pain.md": "Боль в груди",
    "RED_FLAGS.md": "Когда нужна неотложка",
}

META_CARDS = {"INDEX.md", "DISCLAIMER.md"}


def is_blank_answer(text: str | None) -> bool:
    value = (text or "").strip()
    if value.lower() in EMPTY_MARKERS:
        return True
    return len(value) < 40


def looks_like_dump(text: str | None) -> bool:
    value = text or ""
    if "Каталог справочника" in value or "Ключи поиска" in value:
        return True
    return value.count("knowledge/") >= 3


def _section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n+(.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\n{3,}", "\n\n", match.group(1).strip())


def _read_card(knowledge_dir: Path, name: str) -> str:
    path = knowledge_dir / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def select_cards(task: str) -> list[str]:
    q = task.lower()
    chosen: list[str] = []
    if has_red_flag(task):
        chosen.append("RED_FLAGS.md")
    for keys, name in TOPIC_CARDS:
        if any(key in q for key in keys) and name not in chosen:
            chosen.append(name)
    return chosen


def structure_complaint(task: str) -> list[str]:
    q = task.lower()
    rows = [f"как сказано: {task.strip()}"]
    temp = re.search(r"(\d+[.,]?\d*)\s*°?\s*c?", q)
    if "температур" in q or "жар" in q or temp:
        rows.append("температура: названа в тексте" + (f" ({temp.group(1)})" if temp else ""))
    if "кашел" in q:
        kind = "сухой " if "сух" in q else ""
        days = re.search(r"(\d+)\s*дн", q)
        rows.append(f"кашель: {kind}указан" + (f", {days.group(1)} дн." if days else ""))
    if re.search(r"одышк\w* нет|без одышк", q):
        rows.append("одышка: человек пишет, что нет")
    if re.search(r"груд\w* не бол", q):
        rows.append("боль в груди: человек пишет, что нет")
    rows.append("не сказано: возраст, хронические болезни, осмотр, анализы — неизвестно")
    return rows


def compose_reference_report(
    task: str,
    findings: list[str] | None = None,
    hits: list[dict[str, Any]] | None = None,
    knowledge_dir: Path | None = None,
) -> str:
    root = knowledge_dir or Path(__file__).resolve().parents[2] / "workspace" / "knowledge"
    cards = select_cards(task)
    parts = [
        "Справочный отчёт (это не диагноз и не замена врачу).",
        "",
        "Жалоба",
        *[f"- {row}" for row in structure_complaint(task)],
        "",
        "Что это может значить справочно",
    ]
    used: list[str] = []
    for name in cards:
        if name in META_CARDS:
            continue
        human = _section(_read_card(root, name), "Для человека")
        if not human:
            continue
        used.append(f"knowledge/{name}")
        parts.append(CARD_TITLES.get(name, name))
        parts.append(human)
        parts.append("")
    if not used:
        parts.append("В локальном справочнике нет карточки под эту формулировку. Клинику не выдумываем.")
        parts.append("")
    parts.append("Красные флаги по этому тексту")
    if has_red_flag(task):
        parts.append(
            "Есть признаки из порога неотложки. Нужна срочная помощь (103 / 112), "
            "а не ожидание этого чата."
        )
    else:
        parts.append(
            "По буквальному тексту порог скорой не сработал: "
            "отрицания вроде «одышки нет» и «грудь не болит» флагом не считаем. "
            "Это не означает, что всё безопасно."
        )
    parts += [
        "",
        "Чего нельзя решить по сообщению",
        "Причину, возбудителя и название болезни. Даже типичная картина в справочнике "
        "не превращается в диагноз.",
        "",
        "Что обычно делают дальше",
        "Очный осмотр, если так держится несколько дней, становится хуже, "
        "или появляются одышка, боль в груди, кровь в мокроте, спутанность. "
        "Лекарства и дозы не назначаем.",
        "",
        "Карточки: " + (", ".join(used) or "нет"),
    ]
    return strip_diagnosis("\n".join(parts).strip())
