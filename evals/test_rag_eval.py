import json

import pytest

from evals.run_rag_eval import (
    DEFAULT_DATASET,
    _compare,
    _is_abstention,
    _load_dataset,
    _ndcg_at,
    _precision_at,
    _recall_at,
    _reciprocal_rank,
    _reference_coverage,
)


def test_versioned_rag_dataset_has_60_mixed_difficulty_cases() -> None:
    dataset = _load_dataset(DEFAULT_DATASET)
    cases = dataset["cases"]

    assert dataset["dataset_version"] == "journey-rag-eval-v1.0.0"
    assert len(cases) == 60
    assert len({case["id"] for case in cases}) == 60
    assert sum(case["should_abstain"] for case in cases) == 20
    assert any(len(case["expected_document_ids"]) >= 3 for case in cases)
    assert any("hard-negative" in case["tags"] for case in cases)


def test_retrieval_metrics_respect_rank_and_multiple_relevant_documents() -> None:
    ranked = ["doc-b", "doc-c", "doc-a", "doc-d"]
    relevant = {"doc-a", "doc-b"}

    assert _recall_at(ranked, relevant, 1) == 0.5
    assert _recall_at(ranked, relevant, 3) == 1.0
    assert _precision_at(ranked, relevant, 3) == pytest.approx(2 / 3)
    assert _reciprocal_rank(ranked, relevant) == 1.0
    assert 0 < _ndcg_at(ranked, relevant, 5) <= 1


def test_generation_scores_and_abstention_are_explicit() -> None:
    groups = [["整体结构", "整体饮食"], ["极端节食", "长期坚持"]]

    assert _reference_coverage("关注整体结构并避免极端节食", groups) == 1.0
    assert _reference_coverage("只关注整体结构", groups) == 0.5
    assert _is_abstention("受控知识库中没有足够相关资料。", 0) is True
    assert _is_abstention("没有足够资料，但这里有一个引用。", 1) is False
    assert _is_abstention("no-answer：知识库没有对应信息。", 1) is True
    assert _is_abstention("insufficient_context：请补充信息。", 0) is True


def test_baseline_comparison_rejects_different_dataset(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "dataset_sha256": "old",
                "knowledge_bundle_sha256": "same",
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="dataset_sha256_mismatch"):
        _compare(
            {
                "dataset_sha256": "new",
                "knowledge_bundle_sha256": "same",
                "metrics": {},
            },
            baseline,
        )
