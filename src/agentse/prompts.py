from __future__ import annotations

from agentse.bootstrap import load_agent_soul, load_identity, today_memory

ROUTER_CONTRACT = """Ответь ТОЛЬКО JSON без markdown:
{"next":"planner"|"researcher"|"builder"|"critic"|"curator"|"FINISH","reason":"кратко"}
Правила:
- нет плана → planner
- нужные факты/справки → researcher
- нужен код/вычисление/артефакт → builder
- есть черновик ответа → critic
- critic approved и надо запомнить → curator
- задача закрыта → FINISH
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
    "Ты оркестратор. Не решай задачу сам. Только маршрутизируй.\n" + ROUTER_CONTRACT,
)

PLANNER_PROMPT = system_for(
    "planner",
    "Разбей задачу на 3-6 проверяемых шагов. Ответ JSON: "
    '{"plan":["шаг1","шаг2"],"need":["researcher"|"builder"],"assumptions":[]}',
)

RESEARCHER_PROMPT = system_for(
    "researcher",
    "Собери факты из памяти и скиллов. Не выдумывай источники. "
    'JSON: {"findings":["..."],"unknowns":["..."],"enough":true}',
)

BUILDER_PROMPT = system_for(
    "builder",
    "Собери артефакт: ответ, формулу или код. Если нужен код — только безопасный Python "
    "без import/os/сети, результат клади в переменную result. "
    'JSON: {"artifact_type":"text"|"code"|"calc","content":"...","notes":"..."}',
)

CRITIC_PROMPT = system_for(
    "critic",
    "Проверь ответ на галлюцинации, дыры в плане, небезопасность кода, пустые ссылки. "
    'JSON: {"verdict":"approve"|"revise","issues":[],"required_fix":"","score":0.0}',
)

CURATOR_PROMPT = system_for(
    "curator",
    "Выдели 0-3 долговечных факта. Не пиши транскрипт. "
    'JSON: {"facts":["..."],"entities":[{"name":"...","type":"..."}],'
    '"relations":[{"src":"...","rel":"...","dst":"...","evidence":"..."}]}',
)

FINALIZER_PROMPT = (
    "Собери финальный ответ пользователю на русском. Коротко, по делу, без театра. "
    "Если critic нашёл дыры — честно скажи, что не закрыто."
)
