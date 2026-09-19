from agentse.evals.metrics import score_llm_case, task_success


def test_json_route_score():
    case = {
        "kind": "tool_json",
        "expect_json_key": "next",
        "expect_value": "planner",
    }
    assert score_llm_case(case, '{"next":"planner"}') == 1.0
    assert score_llm_case(case, "конечно planner") == 0.0


def test_faithfulness():
    case = {"kind": "faithfulness", "contains": "неизвестно", "forbidden": ["матрица"]}
    assert score_llm_case(case, "НЕИЗВЕСТНО") == 1.0
    assert score_llm_case(case, "Матрица") == 0.0


def test_task_success():
    scores = task_success(
        {"must_include": ["28"], "expect_route_has": ["builder"]},
        "площадь 28",
        ["START", "planner", "builder"],
    )
    assert scores["task_success"] == 1.0
    assert scores["handoff_accuracy"] == 1.0
