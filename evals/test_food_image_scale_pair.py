from evals.run_food_image_scale_pair import metric, percentile, relative_error, score


def test_relative_error_uses_gold_as_denominator() -> None:
    assert relative_error(12, 10) == 0.2
    assert relative_error(8, 10) == 0.2


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5
    assert percentile([], 0.95) == 0


def test_metric_comparisons_include_threshold() -> None:
    assert metric(0.3, 0.3, "<=")["passed"] is True
    assert metric(0.95, 0.95, ">=")["passed"] is True


def result(
    pair: int,
    variant: str,
    *,
    predicted_mass: float,
    schema_valid: bool = True,
) -> dict:
    prediction = (
        {
            "portion_mass_g": predicted_mass,
            "scale_reference_used": variant == "with_ruler",
            "needs_user_correction": True,
        }
        if schema_valid
        else None
    )
    return {
        "id": f"pair-{pair:02d}",
        "variant": variant,
        "gold_mass_g": 10.0,
        "schema_valid": schema_valid,
        "fallback_used": not schema_valid,
        "prediction": prediction,
        "latency_ms": 100,
        "usage": {
            "input_tokens": 100 if schema_valid else 0,
            "output_tokens": 20 if schema_valid else 0,
            "estimated_cost_usd": 0.00001 if schema_valid else 0,
        },
    }


def test_score_uses_only_complete_pairs_for_relative_improvement() -> None:
    results = []
    for pair in range(30):
        results.extend(
            [
                result(pair, "with_ruler", predicted_mass=11),
                result(
                    pair,
                    "without_ruler",
                    predicted_mass=20,
                    schema_valid=pair != 0,
                ),
            ]
        )

    metrics, summary = score(results)

    assert summary["scorable_pairs"] == 29
    assert summary["with_ruler_median_relative_error"] == 0.1
    assert summary["without_ruler_median_relative_error"] == 1.0
    assert summary["relative_error_improvement"] == 0.9
    assert metrics["paired_prediction_coverage"]["passed"] is False
    assert metrics["usage_capture_rate"]["passed"] is False
