from __future__ import annotations

from agentse.bootstrap import load_agent_soul, load_identity, today_memory

ROUTER_CONTRACT = """Ответь ТОЛЬКО JSON без markdown:
{"next":"planner"|"researcher"|"builder"|"critic"|"curator"|"FINISH","reason":"кратко"}
Правила:
- нет плана → planner
- нет карточек/findings → researcher
- нет отчёта → builder
- есть черновик → critic
- critic approved → curator
- закрыто → FINISH
"""


def system_for(agent: str, extra: str = "") -> str:
    identity = load_identity()
    soul = load_agent_soul(agent)
    daily = today_memory()
    return (
        f"{identity}\n\n"
        f"## ROLE SOUL ({agent})\n{soul}\n\n"
        f"## TODAY NOTES\n{daily}\n\n"
        f"{extra}"
    ).strip()


SUPERVISOR_PROMPT = system_for(
    "supervisor",
    "Ты оркестратор MedInfo. Не пиши клинику. Только маршрутизируй.\n" + ROUTER_CONTRACT,
)

PLANNER_PROMPT = system_for(
    "planner",
    "Разложи жалобу на поля и шаги конвейера. Не ставь диагноз. JSON: "
    '{"plan":["шаг"],"symptoms":[],"unknowns":[],"red_flag_words":[]}',
)

RESEARCHER_PROMPT = system_for(
    "researcher",
    "Опирайся только на выданные карточки knowledge/. Не выдумывай клинику. "
    'JSON: {"findings":["файл: мысль"],"unknowns":["..."],"enough":true}',
)

BUILDER_PROMPT = system_for(
    "builder",
    "Собери справочный отчёт по скиллу report-writing. Это НЕ диагноз. "
    "Запрещены фразы: «у вас», «диагноз:», «это точно», названия таблеток. "
    'JSON: {"artifact_type":"text","content":"markdown отчёт","notes":"..."}',
)

CRITIC_PROMPT = system_for(
    "critic",
    "Revise если отчёт ставит диагноз, назначает лечение, молчит про красный флаг, "
    "или не говорит что это не диагноз. "
    'JSON: {"verdict":"approve"|"revise","issues":[],"required_fix":"","score":0.0}',
)

CURATOR_PROMPT = system_for(
    "curator",
    "Не сохраняй симптомы человека. 0 фактов — нормальный исход. "
    'JSON: {"facts":[],"entities":[],"relations":[]}',
)

FINALIZER_PROMPT = (
    "Верни пользователю markdown-отчёт на русском. Сохрани дисклеймер «не диагноз». "
    "Не добавляй новых болезней. Если critic нашёл дыры — исправь формулировки, не ставь диагноз."
)
