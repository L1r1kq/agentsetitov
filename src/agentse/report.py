from __future__ import annotations

from typing import Any

from agentse.medical_guard import has_red_flag, strip_diagnosis

EMPTY_MARKERS = {"", "{}", "[]", "{ }", "null", "none", "{}", "None"}


def is_blank_answer(text: str | None) -> bool:
    value = (text or "").strip()
    if value.lower() in EMPTY_MARKERS:
        return True
    return len(value) < 40


def compose_reference_report(task: str, findings: list[str], hits: list[dict[str, Any]]) -> str:
    lines = [
        "Справочный отчёт (это не диагноз и не замена врачу).",
        "",
        "Структура жалобы",
        f"- как сказано: {task.strip()}",
        "- чего нет в тексте: всё, что человек не назвал (анализы, осмотр, возраст — если молчит, неизвестно).",
        "",
        "Что есть в локальном справочнике",
    ]
    used_files: list[str] = []
    for hit in hits:
        meta = hit.get("meta") or {}
        name = str(meta.get("file") or "knowledge")
        used_files.append(name)
        snippet = " ".join(str(hit.get("text") or "").split())[:320]
        lines.append(f"- {name}: {snippet}")
    for item in findings:
        text = str(item).strip()
        if text and text not in " ".join(lines):
            lines.append(f"- {text[:320]}")
    if len(lines) <= 7:
        lines.append("- подходящая карточка не найдена; клинику из параметров модели не добавляем.")
    lines += ["", "Красные флаги"]
    if has_red_flag(task):
        lines.append(
            "- по тексту сработал порог из knowledge/RED_FLAGS.md: "
            "нужна срочная медицинская помощь (103 / 112), не ожидание этого чата."
        )
    else:
        lines.append(
            "- по буквальному тексту порог RED_FLAGS не сработал "
            "(отрицания вроде «грудь не болит» / «одышки нет» не считаем флагом). "
            "Это не значит, что «всё безопасно»."
        )
    lines += [
        "",
        "Чего нельзя решить по этому сообщению",
        "- причину жара и кашля, вирус/бактерию, «это ОРВИ или нет» — по тексту отличить нельзя.",
        "",
        "Практический следующий шаг",
        "- очный осмотр, если жалоба держится, усиливается или появляются одышка, боль в груди, кровь в мокроте, спутанность;",
        "- лекарства и дозы не назначаем.",
        "",
        "Источники: " + (", ".join(dict.fromkeys(used_files)) or "knowledge/INDEX.md"),
    ]
    return strip_diagnosis("\n".join(lines))
