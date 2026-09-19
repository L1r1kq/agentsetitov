from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentse.config import get_settings

app = typer.Typer(no_args_is_help=True, help="Agentse — локальная мультиагентная система")
console = Console()


@app.command()
def chat(task: str, model: Optional[str] = None) -> None:
    """Прогнать одну задачу через граф агентов."""
    from agentse.graph import AgentRuntime

    runtime = AgentRuntime(model=model)
    result = runtime.invoke(task)
    console.print(Panel(result.get("final_answer") or "", title="Ответ"))
    console.print(f"маршрут: {' → '.join(result.get('route_trace') or [])}")
    console.print(f"критик: {result.get('critique')}")


@app.command("eval-llm")
def eval_llm(models: Optional[str] = None) -> None:
    """Сравнить локальные LLM по агентным критериям."""
    from agentse.evals.llm_bench import run_llm_bench

    settings = get_settings()
    chosen = [m.strip() for m in models.split(",")] if models else settings.eval_model_list
    report = run_llm_bench(chosen)
    table = Table(title="LLM bench")
    table.add_column("model")
    table.add_column("tool_json")
    table.add_column("instr")
    table.add_column("faithful")
    table.add_column("latency")
    table.add_column("total")
    for row in report["models"]:
        table.add_row(
            row["model"],
            f"{row['tool_json']:.2f}",
            f"{row['instruction']:.2f}",
            f"{row['faithfulness']:.2f}",
            f"{row['avg_latency_s']:.2f}s",
            f"{row['score']:.2f}",
        )
    console.print(table)
    console.print(f"победитель: {report['winner']}")
    console.print(f"отчёт: {report['path']}")


@app.command("eval-agent")
def eval_agent(model: Optional[str] = None) -> None:
    """Оценить перформанс мультиагентной системы."""
    from agentse.evals.agent_bench import run_agent_bench

    report = run_agent_bench(model)
    console.print(Panel(str(report["summary"]), title="Agent bench"))
    console.print(f"отчёт: {report['path']}")


@app.command()
def serve() -> None:
    """HTTP UI + API."""
    import uvicorn

    from agentse.observability.logging import setup_logging
    from agentse.observability.tracing import setup_tracing

    settings = get_settings()
    setup_logging(settings.log_level)
    setup_tracing()
    uvicorn.run("agentse.web.app:app", host=settings.host, port=settings.port, reload=False)


@app.command()
def consolidate() -> None:
    """Принудительный цикл куратора памяти (decay + compaction hint)."""
    from agentse.memory.store import HierarchicalMemory

    mem = HierarchicalMemory()
    mem.decay()
    console.print("decay применён, факты остаются в MEMORY.md")


if __name__ == "__main__":
    app()
