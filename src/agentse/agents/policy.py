from __future__ import annotations

from agentse.state import AgentState

VALID = {"planner", "researcher", "builder", "critic", "curator", "FINISH"}


def policy_route(state: AgentState) -> str:
    """Детерминированная политика. На 1.5B-3B это якорь, LLM — опциональный override."""
    plan = state.get("plan") or []
    findings = state.get("findings") or []
    artifacts = state.get("artifacts") or []
    critique = state.get("critique") or {}
    if not plan:
        return "planner"
    if not findings:
        return "researcher"
    if not artifacts:
        return "builder"
    if not critique:
        return "critic"
    if critique.get("verdict") == "revise" and state.get("step", 0) < 6:
        return "builder"
    if critique.get("verdict") == "approve" and not state.get("final_answer"):
        return "curator"
    return "FINISH"


def merge_route(llm_next: str | None, state: AgentState, mode: str) -> str:
    fallback = policy_route(state)
    if mode == "policy":
        return fallback
    if not llm_next or llm_next not in VALID:
        return fallback
    if mode == "llm":
        return llm_next
    # hybrid: политика держит инварианты, LLM может только ускорить допустимый шаг
    if not plan_ready(state):
        return "planner"
    if llm_next == "FINISH" and not (state.get("critique") or {}).get("verdict"):
        return fallback
    if llm_next == "planner" and plan_ready(state):
        return fallback
    last = (state.get("route_trace") or [None])[-1]
    if llm_next == last and llm_next != "builder":
        return fallback
    if llm_next == "researcher" and state.get("findings"):
        return fallback
    return llm_next


def plan_ready(state: AgentState) -> bool:
    return bool(state.get("plan"))
