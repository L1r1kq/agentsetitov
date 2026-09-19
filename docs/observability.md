# Observability — разбор для защиты

Сравнение LangSmith / Langfuse / Langtrace / классический стек: [REPORT.md §10](REPORT.md).

Обязательный минимум (живёт на 8 ГБ):

- Prometheus-метрики на `GET /metrics`
- JSON-логи (structlog)
- File traces в `data/traces/*.jsonl`
- Алерты: петли, ошибки задач, падение TSR, ошибки LLM, отказ sandbox

Опционально (compose profiles):

- `obs`: Prometheus, Grafana :3001, Alertmanager, Tempo, OTEL collector
- `langfuse`: LLM-native traces, когда есть RAM

Специфика агента: смотреть **граф handoff, loop_guard, tokens×steps, drift души**, не только RPS и 5xx.
