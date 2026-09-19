# Выбор LLM — короткая карточка

Железо: M2 / 8 ГБ. Прогнанные модели: `llama3.2:1b`, `qwen2.5:1.5b`, `gemma2:2b`.
Победитель прогона 2026-09-19: **gemma2:2b** (0.78), рядом qwen2.5:1.5b (0.73), llama3.2:1b снят (0.11).
Критерии: JSON-маршрут, instruction, faithfulness, safety, latency.
Протокол: `python3 -m agentse eval-llm`. Живые цифры: `data/eval-runs/llm-latest.json`.
Разбор: [REPORT.md §3](REPORT.md).
