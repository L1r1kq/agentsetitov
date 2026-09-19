from __future__ import annotations

import re

DIAGNOSIS_RE = re.compile(
    r"(у вас\s|вам поставили|диагноз\s*:|это точно\s+\w+|скорее всего у (вас|тебя))",
    re.IGNORECASE,
)
PRESCRIPTION_RE = re.compile(
    r"(примите|назнач\w+|мг\b|антибиотик\w*\s+\w+)",
    re.IGNORECASE,
)
DISCLAIMER_RE = re.compile(r"(не (является )?диагноз|не диагноз|справочн)", re.IGNORECASE)
URGENT_RE = re.compile(
    r"(груд[ие]|одышк|кров[ьи]|сознан|судорог|паралич|перекос лиц|не могу дыш)",
    re.IGNORECASE,
)
HELP_RE = re.compile(r"(срочн|неотлож|скор(ая|ую)|103|112)", re.IGNORECASE)
PHI_RE = re.compile(
    r"(температур|кашел|болит|симптом|тошнот|понос|головн)",
    re.IGNORECASE,
)


def critique_report(task: str, report: str) -> list[str]:
    """Жёсткие нарушения. Отсутствие дисклеймера чинит finalize, не крутит цикл."""
    issues: list[str] = []
    if DIAGNOSIS_RE.search(report):
        issues.append("формулировка похожа на диагноз конкретному человеку")
    if PRESCRIPTION_RE.search(report):
        issues.append("похоже на назначение лекарства")
    if URGENT_RE.search(task) and not HELP_RE.search(report):
        issues.append("в жалобе красный флаг, в отчёте нет срочной помощи")
    return issues


def is_health_fact(text: str) -> bool:
    return bool(PHI_RE.search(text))


def strip_diagnosis(text: str) -> str:
    cleaned = DIAGNOSIS_RE.sub("в справочнике такие формулировки не применяют к человеку ", text)
    if not DISCLAIMER_RE.search(cleaned):
        cleaned = "Справочный отчёт (это не диагноз и не замена врачу).\n\n" + cleaned
    return cleaned
