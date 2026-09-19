# MEMORY

Кураторские факты. Не транскрипт. Если факт устарел — помечаем superseded, не противоречим вслепую.

- (2026-09-19) Железо: Apple M2, 8 ГБ unified memory, Darwin arm64.
- (2026-09-19) Пробовали локально три модели в Ollama: `llama3.2:1b`, `qwen2.5:1.5b`, `gemma2:2b`.
- (2026-09-19) Победитель бенча на M2/8GB: `gemma2:2b` (total 0.78; tool_json 1.00; faithfulness 1.00). `qwen2.5:1.5b` рядом (0.73), лучше в instruction и safety. `llama3.2:1b` непригоден как маршрутизатор (tool_json 0.00).
- (2026-09-19) Движок инференса: Ollama. Не vLLM (нет GPU-сервера), не сырой llama.cpp (хуже UX и смена моделей).
- (2026-09-19) Фреймворк оркестрации: LangGraph StateGraph. Не CrewAI (слабее явный граф), не «без фреймворка» (нужен проверяемый цикл и checkpoint-friendly state).
- (2026-09-19) Память: Hierarchical Cognitive Memory (identity files + episodic + entity graph + curator). Vanilla RAG отвергнут как единственный слой.
- (2026-09-19) Изоляция: Docker Compose (control plane) + отдельный sandbox-контейнер (исполнение) + гибридный local-restricted fallback.
- (2026-09-19) Observability: Prometheus/Grafana/Alertmanager + JSON-логи + file/OTEL traces + опциональный Langfuse.
