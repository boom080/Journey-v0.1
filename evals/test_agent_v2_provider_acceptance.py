from evals.run_agent_v2_provider_acceptance import metric, score, selected_cases


def invocation(*, fallback: bool = False) -> dict:
    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "input_tokens": 100,
        "output_tokens": 20,
        "retries": 0,
        "latency_ms": 900,
        "estimated_cost_usd": 0.0001,
        "fallback_used": fallback,
        "error_code": "provider_unavailable" if fallback else None,
    }


def test_selected_real_agent_v2_cases_are_fixed_and_balanced() -> None:
    cases = selected_cases()
    assert len(cases) == 8
    assert {case["id"] for case in cases} == {
        "plan-001",
        "plan-002",
        "plan-003",
        "plan-004",
        "plan-006",
        "plan-007",
        "plan-009",
        "plan-012",
    }


def test_score_requires_real_schema_safe_no_fallback_invocations() -> None:
    results = [
        {
            "intent_passed": True,
            "schema_valid": True,
            "tools_passed": True,
            "policy_passed": True,
            "router_invocation": invocation(),
            "planner_invocation": invocation(),
        }
        for _ in range(8)
    ]
    metrics, summary = score(
        results,
        expected_provider="deepseek",
        expected_model="deepseek-v4-flash",
        max_cost_usd=0.02,
    )
    assert all(item["passed"] for item in metrics.values())
    assert summary["calls"] == 16
    assert summary["fallbacks"] == 0


def test_lower_is_better_metric_rejects_excess() -> None:
    assert metric(0.03, 0.02, lower_is_better=True)["passed"] is False
