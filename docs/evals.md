# Evals — разбор для защиты

Не скип. Детали и таблицы метрик: [REPORT.md §9](REPORT.md).

```bash
python3 -m agentse eval-llm     # три локальные модели
python3 -m agentse eval-agent   # граф целиком
./scripts/nightly_eval.sh       # непрерывный контур
```

Артефакты: `data/eval-runs/llm-latest.json`, `agent-latest.json`.
Метрики: `agentse_eval_score{suite,model,metric}`.
Алерт: `AgentseEvalDrop` при TSR < 0.5.

Судья LLM-кейсов — детерминированный парсер: маленькая модель не должна оценивать сама себя.
