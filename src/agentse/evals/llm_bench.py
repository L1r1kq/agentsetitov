from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from agentse.config import get_settings
from agentse.evals.datasets import LLM_CASES
from agentse.evals.metrics import score_llm_case
from agentse.llm import OllamaClient
from agentse.observability.metrics import EVAL_SCORE


def run_llm_bench(models: list[str] | None = None) -> dict[str, Any]:
    settings = get_settings()
    models = models or settings.eval_model_list
    rows: list[dict[str, Any]] = []
    for model in models:
        client = OllamaClient(settings, model=model)
        per_kind: dict[str, list[float]] = {}
        latencies: list[float] = []
        details = []
        for case in LLM_CASES:
            try:
                result = client.generate(case["prompt"], temperature=0.1, max_tokens=180)
                text = result.text
                latency = result.latency_s
            except Exception as exc:
                text = ""
                latency = 0.0
                details.append({"id": case["id"], "error": repr(exc), "score": 0.0})
                per_kind.setdefault(case["kind"], []).append(0.0)
                continue
            score = score_llm_case(case, text)
            per_kind.setdefault(case["kind"], []).append(score)
            latencies.append(latency)
            details.append({"id": case["id"], "score": score, "latency_s": latency, "text": text[:240]})
        tool_json = mean(per_kind.get("tool_json") or [0])
        instruction = mean(per_kind.get("instruction") or [0])
        faithfulness = mean(per_kind.get("faithfulness") or [0])
        safety = mean(per_kind.get("safety") or [0])
        avg_lat = mean(latencies) if latencies else 99.0
        # агентность: JSON-маршрутизация и верность контексту важнее «красоты»
        total = 0.35 * tool_json + 0.25 * faithfulness + 0.20 * instruction + 0.15 * safety + 0.05 * max(0, 1 - avg_lat / 20)
        row = {
            "model": model,
            "tool_json": tool_json,
            "instruction": instruction,
            "faithfulness": faithfulness,
            "safety": safety,
            "avg_latency_s": avg_lat,
            "score": total,
            "details": details,
        }
        rows.append(row)
        for metric, value in {
            "tool_json": tool_json,
            "instruction": instruction,
            "faithfulness": faithfulness,
            "safety": safety,
            "total": total,
        }.items():
            EVAL_SCORE.labels(suite="llm", model=model, metric=metric).set(value)
        client.close()
    rows.sort(key=lambda r: r["score"], reverse=True)
    report = {
        "ts": datetime.now(UTC).isoformat(),
        "hardware": "Apple M2 8GB",
        "criteria": [
            "tool/json reliability",
            "instruction following",
            "context faithfulness / anti-hallucination",
            "safety refusal",
            "latency on 8GB",
        ],
        "models": rows,
        "winner": rows[0]["model"] if rows else None,
    }
    path = settings.eval_runs_dir / f"llm-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = settings.eval_runs_dir / "llm-latest.json"
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["path"] = str(path)
    return report


def write_markdown(report: dict[str, Any], dest: Path) -> None:
    lines = [
        "# LLM bench",
        "",
        f"Время: {report['ts']}",
        f"Победитель: **{report.get('winner')}**",
        "",
        "| model | tool_json | instruction | faithfulness | safety | latency | total |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["models"]:
        lines.append(
            f"| {row['model']} | {row['tool_json']:.2f} | {row['instruction']:.2f} | "
            f"{row['faithfulness']:.2f} | {row['safety']:.2f} | {row['avg_latency_s']:.2f}s | {row['score']:.2f} |"
        )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
