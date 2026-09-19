from __future__ import annotations

import json
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from agentse.config import get_settings
from agentse.evals.datasets import AGENT_CASES
from agentse.evals.metrics import task_success
from agentse.graph import AgentRuntime
from agentse.observability.metrics import EVAL_SCORE


def run_agent_bench(model: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    runtime = AgentRuntime(settings, model=model)
    cases = []
    for case in AGENT_CASES:
        started = datetime.now(UTC)
        result = runtime.invoke(case["task"], session_id=f"eval-{case['id']}")
        scores = task_success(case, result.get("final_answer") or "", result.get("route_trace") or [])
        critic = result.get("critique") or {}
        looped = 1.0 if (result.get("step") or 0) >= settings.max_steps else 0.0
        tool_fail = 0.0
        for art in result.get("artifacts") or []:
            sandbox = art.get("sandbox") or {}
            if sandbox and sandbox.get("ok") is False:
                tool_fail = 1.0
        row = {
            "id": case["id"],
            "task_success": scores["task_success"],
            "handoff_accuracy": scores["handoff_accuracy"],
            "critic_score": float(critic.get("score") or 0),
            "steps": result.get("step"),
            "looped": looped,
            "tool_fail": tool_fail,
            "route": result.get("route_trace"),
            "answer": (result.get("final_answer") or "")[:500],
            "started": started.isoformat(),
        }
        cases.append(row)
    summary = {
        "task_success_rate": mean(c["task_success"] for c in cases),
        "handoff_accuracy": mean(c["handoff_accuracy"] for c in cases),
        "avg_critic_score": mean(c["critic_score"] for c in cases),
        "loop_rate": mean(c["looped"] for c in cases),
        "tool_error_rate": mean(c["tool_fail"] for c in cases),
        "avg_steps": mean(c["steps"] or 0 for c in cases),
    }
    for key, value in summary.items():
        EVAL_SCORE.labels(suite="agent", model=model or settings.model, metric=key).set(value)
    report = {
        "ts": datetime.now(UTC).isoformat(),
        "model": model or settings.model,
        "summary": summary,
        "cases": cases,
        "how_to_monitor": {
            "nightly": "agentse eval-agent && agentse eval-llm",
            "prometheus": ["agentse_eval_score", "agentse_task_latency_seconds", "agentse_loop_guard_total"],
            "alert": "TSR drop > 20% vs 7d baseline or loop_rate > 0.15",
        },
    }
    path = settings.eval_runs_dir / f"agent-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (settings.eval_runs_dir / "agent-latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["path"] = str(path)
    return report
