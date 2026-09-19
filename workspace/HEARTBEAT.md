# HEARTBEAT.md

Автономные пульсы, когда система жива без нового чата.

1. Раз в ночь: `agentse eval-llm` и `agentse eval-agent`. Пишем JSON в `data/eval-runs/` и выставляем `agentse_eval_score`.
2. После eval: curator-цикл `agentse consolidate` (decay графа).
3. Если `task_success_rate` упал > 20% к скользящим 7 дням — алерт `AgentseEvalDrop`.
4. Если `agentse_loop_guard_total` растёт — алерт на деградацию маршрутизации.
5. Не запускать heartbeat-инструменты, которые требуют сеть наружу.
