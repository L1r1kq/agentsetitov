# Agentse

Локальная мультиагентная система для инженерных задач: supervisor + специалисты, иерархическая память вместо RAG, evals и наблюдаемость.

Железо этого репозитория: **Apple M2, 8 ГБ**. Дефолтная модель — `gemma2:2b` в **Ollama** (победитель локального бенча 2026-09-19).

## Быстрый старт

```bash
python3 -m pip install -e ".[dev]"
cp .env.example .env
# Ollama уже должен слушать :11434, модели:
#   ollama pull llama3.2:1b && ollama pull qwen2.5:1.5b && ollama pull gemma2:2b
python3 -m pytest -q
python3 -m agentse eval-llm
python3 -m agentse chat "Почему память агента не должна быть только RAG?"
python3 -m agentse serve   # http://127.0.0.1:8080
```

## Что внутри

| Слой | Где |
|---|---|
| ТЗ | [docs/TZ.md](docs/TZ.md) |
| Отчёт к защите | [docs/REPORT.md](docs/REPORT.md) |
| C4 / Sequence | [docs/architecture/](docs/architecture/) |
| Soul / identity | [workspace/](workspace/) |
| Скиллы | [skills/](skills/) |
| Изоляция | [deploy/docker-compose.yml](deploy/docker-compose.yml) |
| Evals | `python3 -m agentse eval-llm` / `eval-agent` |
| Метрики | `GET /metrics` + Prometheus/Grafana |

## Команда агентов

`supervisor → planner → researcher → builder → critic → curator → FINISH`

Маршрутизация **hybrid**: детерминированная политика якорит маленькую модель, LLM может сдвинуть маршрут, но не закрыть задачу без критика.
