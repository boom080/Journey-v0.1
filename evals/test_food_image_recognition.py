import pytest
from pydantic import ValidationError

from evals.run_food_image_recognition import (
    EXPECTED_COHORTS,
    RecognitionPrediction,
    contains_forbidden_estimate,
    name_hit,
    percentile,
    score,
)


def test_prediction_schema_rejects_extra_estimate_fields() -> None:
    with pytest.raises(ValidationError):
        RecognitionPrediction.model_validate(
            {
                "is_food": True,
                "candidates": [
                    {
                        "name_zh": "苹果",
                        "name_en": "apple",
                        "confidence": "medium",
                    }
                ],
                "confidence": "medium",
                "should_abstain": False,
                "needs_user_correction": True,
                "portion_mass_g": 100,
            }
        )


def test_prediction_schema_requires_consistent_abstention() -> None:
    with pytest.raises(ValidationError):
        RecognitionPrediction.model_validate(
            {
                "is_food": False,
                "candidates": [
                    {
                        "name_zh": "苹果",
                        "name_en": "apple",
                        "confidence": "low",
                    }
                ],
                "confidence": "low",
                "should_abstain": True,
                "needs_user_correction": True,
            }
        )


def test_forbidden_estimate_detector_checks_nested_keys_and_values() -> None:
    assert contains_forbidden_estimate({"portion": {"grams": 100}}) is True
    assert contains_forbidden_estimate({"candidates": [{"name_zh": "苹果"}]}) is False
    assert (
        contains_forbidden_estimate({"candidates": [{"name_zh": "苹果 80千卡"}]})
        is True
    )


def test_name_hit_supports_chinese_and_english_aliases() -> None:
    expected = [{"canonical_en": "mapo tofu", "aliases": ["麻婆豆腐"]}]
    assert name_hit(["麻婆豆腐"], expected) is True
    assert name_hit(["Mapo tofu dish"], expected) is True
    assert name_hit(["fried rice"], expected) is False


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5
    assert percentile([], 0.95) == 0


def fixtures() -> tuple[list[dict], list[dict]]:
    entries = []
    results = []
    index = 0
    for cohort, count in EXPECTED_COHORTS.items():
        for _ in range(count):
            index += 1
            sample_id = f"sample-{index:02d}"
            is_food = cohort != "nonfood"
            entries.append(
                {
                    "id": sample_id,
                    "cohort": cohort,
                    "gold": {
                        "top3_metric_eligible": is_food,
                        "should_abstain": not is_food,
                        "names": [
                            {
                                "canonical_en": "apple",
                                "aliases": ["苹果"],
                            }
                        ],
                    },
                }
            )
            prediction = {
                "is_food": is_food,
                "candidates": (
                    [
                        {
                            "name_zh": "苹果",
                            "name_en": "apple",
                            "confidence": "medium",
                        }
                    ]
                    if is_food
                    else []
                ),
                "confidence": "medium",
                "should_abstain": not is_food,
                "needs_user_correction": True,
            }
            results.append(
                {
                    "id": sample_id,
                    "schema_valid": True,
                    "forbidden_estimate_detected": False,
                    "fallback_used": False,
                    "prediction": prediction,
                    "latency_ms": 100,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "estimated_cost_usd": 0.00001,
                    },
                }
            )
    return entries, results


def test_score_passes_a_perfect_recognition_run() -> None:
    entries, results = fixtures()
    metrics, summary = score(entries, results, max_estimated_cost_usd=0.02)

    assert all(item["passed"] for item in metrics.values())
    assert metrics["overall_food_top3_name_hit_rate"]["numerator"] == 55
    assert metrics["chinese_home_meal_top3_name_hit_rate"]["denominator"] == 20
    assert metrics["nonfood_abstention_rate"]["numerator"] == 5
    assert summary["provider_calls"] == 60


def test_score_counts_schema_failure_against_all_hard_gates() -> None:
    entries, results = fixtures()
    results[0] = {
        **results[0],
        "schema_valid": False,
        "fallback_used": True,
        "prediction": None,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0,
        },
    }
    metrics, _ = score(entries, results, max_estimated_cost_usd=0.02)

    assert metrics["schema_valid_rate"]["passed"] is False
    assert metrics["needs_user_correction_rate"]["passed"] is False
    assert metrics["provider_fallback_count"]["passed"] is False
    assert metrics["usage_capture_rate"]["passed"] is False
