from __future__ import annotations

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest
from prometheus_client import start_http_server

AGENT_STEPS = Counter(
    "agentse_agent_steps_total",
    "Шаги агентов",
    ["agent"],
)
AGENT_HANDOFFS = Counter(
    "agentse_handoffs_total",
    "Handoff между агентами",
    ["src", "dst"],
)
TASKS = Counter(
    "agentse_tasks_total",
    "Задачи оркестратора",
    ["status"],
)
TASK_LATENCY = Histogram(
    "agentse_task_latency_seconds",
    "Латентность end-to-end задачи",
    buckets=(1, 3, 8, 15, 30, 60, 120, 240),
)
LLM_REQUESTS = Counter(
    "agentse_llm_requests_total",
    "Запросы к LLM",
    ["model", "status"],
)
LLM_LATENCY = Histogram(
    "agentse_llm_latency_seconds",
    "Латентность LLM",
    ["model"],
    buckets=(0.2, 0.5, 1, 2, 4, 8, 16, 32, 64),
)
LLM_TOKENS = Counter(
    "agentse_llm_tokens_total",
    "Токены LLM",
    ["model", "kind"],
)
TOOL_CALLS = Counter(
    "agentse_tool_calls_total",
    "Вызовы инструментов",
    ["tool", "status"],
)
SANDBOX_DENIES = Counter(
    "agentse_sandbox_denies_total",
    "Отказы песочницы",
    ["reason"],
)
MEMORY_WRITES = Counter(
    "agentse_memory_writes_total",
    "Записи в память",
    ["layer"],
)
MEMORY_HITS = Counter(
    "agentse_memory_hits_total",
    "Попадания поиска памяти",
    ["layer"],
)
CRITIC_VERDICTS = Counter(
    "agentse_critic_verdicts_total",
    "Вердикты критика",
    ["verdict"],
)
LOOPS = Counter(
    "agentse_loop_guard_total",
    "Срабатывания защиты от циклов",
)
EVAL_SCORE = Gauge(
    "agentse_eval_score",
    "Последний eval-score",
    ["suite", "model", "metric"],
)
ACTIVE_SESSIONS = Gauge(
    "agentse_active_sessions",
    "Активные сессии",
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)


def metrics_app():
    from starlette.responses import Response

    def endpoint(_request=None):
        return Response(generate_latest(REGISTRY), media_type="text/plain")

    return endpoint
