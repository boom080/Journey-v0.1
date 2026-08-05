from evals.run_text_provider_acceptance import score, select_router_cases


def invocation(**overrides):
    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "input_tokens": 100,
        "output_tokens": 20,
        "retries": 0,
        "latency_ms": 500,
        "estimated_cost_usd": 0.0001,
        "fallback_used": False,
        "error_code": None,
        **overrides,
    }


def result(capability: str, *, passed: bool = True, **overrides):
    return {
        "id": f"{capability}-1",
        "capability": capability,
        "passed": passed,
        "invocation": invocation(**overrides),
    }


def test_router_selection_is_stratified_by_expected_intents() -> None:
    cases = [
        {"id": "f1", "expected": ["food"]},
        {"id": "f2", "expected": ["food"]},
        {"id": "f3", "expected": ["food"]},
        {"id": "a1", "expected": ["activity"]},
        {"id": "a2", "expected": ["activity"]},
        {"id": "a3", "expected": ["activity"]},
    ]

    selected = select_router_cases(cases, per_expected_group=2)

    assert [case["id"] for case in selected] == ["f1", "f2", "a1", "a2"]


def test_score_passes_real_provider_results_without_fallback() -> None:
    results = [
        result("intent_classification"),
        result("food_text_parse"),
        result("activity_text_parse"),
    ]

    metrics, summary = score(
        results,
        expected_provider="deepseek",
        expected_model="deepseek-v4-flash",
        max_cost_usd=0.02,
    )

    assert all(metric["passed"] for metric in metrics.values())
    assert summary["calls"] == 3
    assert summary["fallbacks"] == 0


def test_score_fails_mock_or_fallback_even_when_outputs_match() -> None:
    results = [
        result("intent_classification", provider="mock", fallback_used=True),
        result("food_text_parse"),
        result("activity_text_parse"),
    ]

    metrics, _ = score(
        results,
        expected_provider="deepseek",
        expected_model="deepseek-v4-flash",
        max_cost_usd=0.02,
    )

    assert metrics["provider_model_match_rate"]["passed"] is False
    assert metrics["schema_no_fallback_rate"]["passed"] is False
