from agentse.agents.policy import merge_route, policy_route


def test_policy_order():
    assert policy_route({"plan": []}) == "planner"
    assert policy_route({"plan": ["a"], "findings": []}) == "researcher"
    assert policy_route({"plan": ["a"], "findings": ["f"], "artifacts": []}) == "builder"
    assert policy_route({"plan": ["a"], "findings": ["f"], "artifacts": [{}], "critique": {}}) == "critic"
    assert (
        policy_route(
            {
                "plan": ["a"],
                "findings": ["f"],
                "artifacts": [{}],
                "critique": {"verdict": "approve"},
                "final_answer": "",
            }
        )
        == "curator"
    )


def test_hybrid_blocks_early_finish():
    state = {"plan": ["a"], "findings": [], "artifacts": [], "critique": {}}
    assert merge_route("FINISH", state, "hybrid") != "FINISH"
    assert merge_route("researcher", state, "hybrid") == "researcher"


def test_hybrid_forces_planner_without_plan():
    assert merge_route("researcher", {"plan": []}, "hybrid") == "planner"


def test_hybrid_no_repeat_researcher():
    state = {
        "plan": ["a"],
        "findings": ["f"],
        "artifacts": [],
        "critique": {},
        "route_trace": ["researcher"],
    }
    assert merge_route("researcher", state, "hybrid") == "builder"
