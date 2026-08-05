from evals.run_agent_v3_provider_acceptance import selected_cases


def test_selected_real_agent_v3_cases_are_fixed_checkpoint_cases() -> None:
    cases = selected_cases()
    assert len(cases) == 4
    assert {case["id"] for case in cases} == {
        "checkpoint-001",
        "checkpoint-002",
        "checkpoint-003",
        "checkpoint-005",
    }
    assert all(case["kind"] == "checkpoint" for case in cases)
