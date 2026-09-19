from __future__ import annotations

import re

DIAGNOSIS_RE = re.compile(
    r"(у вас\s|вам поставили|диагноз\s*:|это точно\s+\w+|скорее всего у (вас|тебя))",
    re.IGNORECASE,
)
PRESCRIPTION_RE = re.compile(
    r"(примите\b|вам назнач|\b\d+\s*мг\b|курс антибиотик)",
    re.IGNORECASE,
)
DISCLAIMER_RE = re.compile(r"(не (является )?диагноз|не диагноз|справочн)", re.IGNORECASE)
HELP_RE = re.compile(r"(срочн|неотлож|скор(ая|ую)|103|112)", re.IGNORECASE)


def has_red_flag(task: str) -> bool:
    """Положительные красные флаги. «грудь не болит» / «одышки нет» — не флаг."""
    t = task.lower()
    if re.search(r"(потеря|потерял\w*) сознан|судорог|паралич|перекос лиц|не могу дыш", t):
        return True
    if re.search(r"(рвота кров|кров[ьюи].*(мокрот|ступ|рвот)|чёрный стул)", t):
        return True
    denied = bool(re.search(r"(одышк\w* нет|без одышк|одышки нет)", t))
    if re.search(r"одышк", t) and not denied:
        return True
    chest_denied = bool(re.search(r"груд\w* не бол", t))
    if re.search(r"(боль в груди|давящ\w* боль|жж[её]т за грудин|холодн\w* пот)", t) and not chest_denied:
        return True
    if re.search(r"давящ\w*.*груд|груд\w*.*давящ", t) and not chest_denied:
        return True
    return False
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
    if has_red_flag(task) and not HELP_RE.search(report):
        issues.append("в жалобе красный флаг, в отчёте нет срочной помощи")
    return issues


def is_health_fact(text: str) -> bool:
    return bool(PHI_RE.search(text))


def strip_diagnosis(text: str) -> str:
    cleaned = DIAGNOSIS_RE.sub("в справочнике такие формулировки не применяют к человеку ", text)
    if not DISCLAIMER_RE.search(cleaned):
        cleaned = "Справочный отчёт (это не диагноз и не замена врачу).\n\n" + cleaned
    return cleaned
