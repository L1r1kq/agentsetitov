from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from agentse.agents.policy import merge_route
from agentse.config import Settings, get_settings
from agentse.medical_guard import critique_report, is_health_fact, strip_diagnosis
from agentse.report import compose_reference_report, is_blank_answer
from agentse.llm import LLMResult, OllamaClient, parse_json_object
from agentse.observability.metrics import (
    AGENT_HANDOFFS,
    AGENT_STEPS,
    CRITIC_VERDICTS,
    LOOPS,
    TASK_LATENCY,
    TASKS,
)
from agentse.observability.tracing import start_span, trace_event
from agentse.prompts import (
    BUILDER_PROMPT,
    CRITIC_PROMPT,
    CURATOR_PROMPT,
    FINALIZER_PROMPT,
    PLANNER_PROMPT,
    RESEARCHER_PROMPT,
    SUPERVISOR_PROMPT,
)
from agentse.state import AgentState
from agentse.tools.registry import ToolRegistry


class AgentRuntime:
    def __init__(self, settings: Settings | None = None, model: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm = OllamaClient(self.settings, model=model)
        self.tools = ToolRegistry(self.settings)
        self.graph = self._build()

    def _ask(self, system: str, user: str, fmt_json: bool = True) -> LLMResult:
        return self.llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            format_json=fmt_json,
        )

    def _safe_json(self, result: LLMResult) -> dict[str, Any]:
        try:
            return parse_json_object(result.text)
        except (ValueError, json.JSONDecodeError):
            return {"raw": result.text}

    def supervisor(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="supervisor").inc()
        payload = {
            "task": state.get("task"),
            "plan": state.get("plan"),
            "findings": state.get("findings"),
            "artifacts": [a.get("artifact_type") for a in state.get("artifacts") or []],
            "critique": state.get("critique"),
            "step": state.get("step", 0),
        }
        llm_next = None
        try:
            result = self._ask(SUPERVISOR_PROMPT, json.dumps(payload, ensure_ascii=False))
            llm_next = self._safe_json(result).get("next")
        except Exception:
            llm_next = None
        nxt = merge_route(llm_next, state, self.settings.routing_mode)
        if state.get("step", 0) >= self.settings.max_steps:
            LOOPS.inc()
            nxt = "FINISH"
        prev = (state.get("route_trace") or ["START"])[-1]
        AGENT_HANDOFFS.labels(src=prev, dst=nxt).inc()
        trace_event("handoff", src=prev, dst=nxt)
        return {
            "next_agent": nxt,
            "route_trace": (state.get("route_trace") or []) + [nxt],
            "step": state.get("step", 0) + 1,
            "messages": [AIMessage(content=f"route:{nxt}")],
        }

    def planner(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="planner").inc()
        self.tools.call("skill_load", name="symptom-intake")
        self.tools.call("skill_load", name="planning")
        hits = self.tools.call("knowledge_search", query=state["task"], limit=4)
        result = self._ask(
            PLANNER_PROMPT,
            f"Задача: {state['task']}\nПамять: {json.dumps(hits, ensure_ascii=False)}",
        )
        data = self._safe_json(result)
        plan = data.get("plan") or [state["task"]]
        if not isinstance(plan, list):
            plan = [str(plan)]
        self.tools.memory.write_episodic(state.get("session_id", "default"), "plan", " | ".join(map(str, plan)))
        return {"plan": [str(x) for x in plan], "memory_hits": [h["text"] for h in hits]}

    def researcher(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="researcher").inc()
        skill = self.tools.call("skill_load", name="medical-reference")
        hits = self.tools.call("knowledge_search", query=state["task"], limit=6)
        result = self._ask(
            RESEARCHER_PROMPT,
            f"Жалоба: {state['task']}\nПлан: {state.get('plan')}\n"
            f"Скилл:\n{skill[:1200]}\nКарточки: {json.dumps(hits, ensure_ascii=False)}",
        )
        data = self._safe_json(result)
        findings = data.get("findings") or [h["text"] for h in hits] or [result.text]
        if not isinstance(findings, list):
            findings = [str(findings)]
        return {"findings": [str(x) for x in findings], "memory_hits": [h["text"] for h in hits]}

    def builder(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="builder").inc()
        self.tools.call("skill_load", name="report-writing")
        hits = self.tools.call("knowledge_search", query=state["task"], limit=5)
        fallback = compose_reference_report(state["task"], list(state.get("findings") or []), hits)
        result = self._ask(
            BUILDER_PROMPT,
            f"Жалоба: {state['task']}\nПлан: {state.get('plan')}\nКарточки: {state.get('findings')}\n"
            f"Замечания критика: {state.get('critique')}\n"
            f"Если не уверен — верни этот черновик как content:\n{fallback[:1800]}",
            fmt_json=True,
        )
        data = self._safe_json(result)
        content = str(data.get("content") or result.text)
        if is_blank_answer(content):
            content = fallback
        artifact = {
            "artifact_type": data.get("artifact_type") or "text",
            "content": content,
            "notes": data.get("notes") or "",
        }
        if artifact["artifact_type"] in {"code", "calc"} or "result =" in content:
            code = content
            if "```" in code:
                code = code.split("```")[1]
                if code.startswith("python"):
                    code = code[6:]
            exec_result = self.tools.call("sandbox_exec", code=code)
            artifact["sandbox"] = exec_result
            if exec_result.get("ok") and exec_result.get("stdout"):
                artifact["content"] = f"{content}\n\nsandbox: {exec_result['stdout'].strip()}"
        artifacts = list(state.get("artifacts") or [])
        artifacts.append(artifact)
        return {"artifacts": artifacts}

    def critic(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="critic").inc()
        self.tools.call("skill_load", name="critique")
        last = (state.get("artifacts") or [{}])[-1]
        result = self._ask(
            CRITIC_PROMPT,
            f"Задача: {state['task']}\nПлан: {state.get('plan')}\nФакты: {state.get('findings')}\n"
            f"Артефакт: {json.dumps(last, ensure_ascii=False)[:3000]}",
        )
        data = self._safe_json(result)
        verdict = data.get("verdict") if data.get("verdict") in {"approve", "revise"} else "approve"
        issues = [str(x) for x in (data.get("issues") or []) if x]
        guard = critique_report(state.get("task") or "", str(last.get("content") or ""))
        issues.extend(guard)
        if last.get("sandbox") and last["sandbox"].get("ok") is False:
            guard.append("sandbox failed")
            issues.append("sandbox failed")
        if guard:
            verdict = "revise"
            data["required_fix"] = data.get("required_fix") or guard[0]
        data["issues"] = issues
        score = float(data.get("score") or (0.8 if verdict == "approve" else 0.4))
        CRITIC_VERDICTS.labels(verdict=verdict).inc()
        critique = {
            "verdict": verdict,
            "issues": data.get("issues") or [],
            "required_fix": data.get("required_fix") or "",
            "score": score,
        }
        return {"critique": critique, "scores": {**(state.get("scores") or {}), "critic": score}}

    def curator(self, state: AgentState) -> dict[str, Any]:
        AGENT_STEPS.labels(agent="curator").inc()
        self.tools.call("skill_load", name="memory-curation")
        last = (state.get("artifacts") or [{}])[-1]
        result = self._ask(
            CURATOR_PROMPT,
            f"Задача: {state['task']}\nОтвет: {last.get('content', '')[:1500]}",
        )
        data = self._safe_json(result)
        session_id = state.get("session_id", "default")
        for fact in data.get("facts") or []:
            if is_health_fact(str(fact)):
                continue
            self.tools.call("memory_write", fact=str(fact), session_id=session_id, kind="fact")
        for ent in data.get("entities") or []:
            if isinstance(ent, dict) and ent.get("name"):
                self.tools.memory.upsert_entity(str(ent["name"]), str(ent.get("type") or "thing"))
        for rel in data.get("relations") or []:
            if isinstance(rel, dict) and rel.get("src") and rel.get("dst"):
                self.tools.memory.relate(
                    str(rel["src"]),
                    str(rel.get("rel") or "related"),
                    str(rel["dst"]),
                    str(rel.get("evidence") or state["task"]),
                )
        final = self._finalize(state, last)
        return {"final_answer": final}

    def _grounded_report(self, state: AgentState, last: dict[str, Any]) -> str:
        hits = self.tools.call("knowledge_search", query=state.get("task") or "", limit=5)
        artifact = str(last.get("content") or "")
        if not is_blank_answer(artifact):
            return strip_diagnosis(artifact)
        return compose_reference_report(state.get("task") or "", list(state.get("findings") or []), hits)

    def _finalize(self, state: AgentState, last: dict[str, Any]) -> str:
        grounded = self._grounded_report(state, last)
        try:
            result = self._ask(
                FINALIZER_PROMPT,
                f"Жалоба: {state['task']}\nЧерновик (верни его почти дословно, можно чуть сжать):\n{grounded[:2500]}\n"
                f"Критика: {state.get('critique')}\nНе отвечай пустым JSON.",
                fmt_json=False,
            )
            if is_blank_answer(result.text):
                return grounded
            return strip_diagnosis(result.text)
        except Exception:
            return grounded

    def _route(self, state: AgentState) -> str:
        nxt = state.get("next_agent") or "FINISH"
        if nxt == "FINISH":
            return END
        return nxt

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("supervisor", self.supervisor)
        g.add_node("planner", self.planner)
        g.add_node("researcher", self.researcher)
        g.add_node("builder", self.builder)
        g.add_node("critic", self.critic)
        g.add_node("curator", self.curator)
        g.add_edge(START, "supervisor")
        g.add_conditional_edges(
            "supervisor",
            self._route,
            {
                "planner": "planner",
                "researcher": "researcher",
                "builder": "builder",
                "critic": "critic",
                "curator": "curator",
                END: END,
            },
        )
        for node in ("planner", "researcher", "builder", "critic", "curator"):
            g.add_edge(node, "supervisor")
        return g.compile()

    def invoke(self, task: str, session_id: str | None = None) -> AgentState:
        session_id = session_id or uuid.uuid4().hex[:10]
        import time

        started = time.perf_counter()
        TASKS.labels(status="started").inc()
        init: AgentState = {
            "messages": [HumanMessage(content=task)],
            "task": task,
            "session_id": session_id,
            "plan": [],
            "findings": [],
            "artifacts": [],
            "critique": {},
            "memory_hits": [],
            "next_agent": "planner",
            "step": 0,
            "route_trace": ["START"],
            "final_answer": "",
            "scores": {},
        }
        with start_span("task", session_id=session_id, task=task[:120]):
            try:
                result = self.graph.invoke(init)
                TASKS.labels(status="ok").inc()
            except Exception:
                TASKS.labels(status="error").inc()
                raise
            finally:
                TASK_LATENCY.observe(time.perf_counter() - started)
        if is_blank_answer(result.get("final_answer")):
            last = (result.get("artifacts") or [{}])[-1]
            result["final_answer"] = self._grounded_report(result, last)
        self.tools.memory.write_episodic(session_id, "answer", result["final_answer"][:1000])
        self.tools.memory.decay()
        return result
