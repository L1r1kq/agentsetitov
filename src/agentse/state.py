from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


AgentName = Literal[
    "supervisor",
    "planner",
    "researcher",
    "builder",
    "critic",
    "curator",
    "FINISH",
]


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    task: str
    session_id: str
    plan: list[str]
    findings: list[str]
    artifacts: list[dict[str, Any]]
    critique: dict[str, Any]
    memory_hits: list[str]
    next_agent: str
    step: int
    route_trace: list[str]
    final_answer: str
    scores: dict[str, float]
