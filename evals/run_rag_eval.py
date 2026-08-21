"""Versioned Journey RAG evaluation with explicit Mock/real separation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.model_router import ModelRouter
from app.agent.workflows import run_knowledge
from app.core.database import engine
from app.core.settings import get_settings
from app.knowledge.embedding import EMBEDDING_VERSION
from app.knowledge.ingest import BUNDLE_PATH, ingest_builtin_knowledge
from app.knowledge.retriever import RETRIEVER_VERSION, RetrievedChunk, retrieve
from app.models.knowledge import KnowledgeDocument, KnowledgeSource

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "datasets" / "rag_eval_v1.json"
SCORING_VERSION = "journey-rag-eval-scorer-1.1.0"
RAG_CONFIGS = {
    "rag-v1": {"top_k": 3, "minimum_score": 0.16, "rerank": False},
    "rag-v2-candidate": {"top_k": 5, "minimum_score": 0.10, "rerank": True},
}
THRESHOLDS = {
    "recall_at_1": 0.70,
    "recall_at_3": 0.85,
    "recall_at_5": 0.90,
    "mrr": 0.78,
    "groundedness": 0.70,
    "answer_relevance": 0.70,
    "citation_correctness": 0.80,
    "abstention_accuracy": 0.80,
}
ABSTENTION_MARKERS = (
    "insufficient_context",
    "no-answer",
    "无法回答",
    "没有足够",
    "信息不足",
    "无法从",
    "不能确定",
    "不知道",
    "无法判断",
    "不提供",
    "请咨询",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _stable_key(slug: str, external_id: str) -> str:
    return f"{slug}/{external_id}"


def _document_keys(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(
            KnowledgeDocument.id, KnowledgeDocument.external_id, KnowledgeSource.slug
        ).join(KnowledgeSource, KnowledgeSource.id == KnowledgeDocument.source_id)
    )
    return {
        str(document_id): _stable_key(slug, external_id)
        for document_id, external_id, slug in rows
    }


def _ranked_keys(chunks: list[RetrievedChunk], key_by_id: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for chunk in chunks:
        key = key_by_id.get(chunk.document_id, chunk.document_id)
        if key not in seen:
            result.append(key)
            seen.add(key)
    return result


def _recall_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def _precision_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / k if relevant else 0.0


def _reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for index, key in enumerate(ranked, start=1):
        if key in relevant:
            return 1 / index
    return 0.0


def _ndcg_at(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(
        1 / math.log2(index + 2)
        for index, key in enumerate(ranked[:k])
        if key in relevant
    )
    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


def _reference_coverage(answer: str, groups: list[list[str]]) -> float:
    if not groups:
        return 1.0
    return sum(any(term in answer for term in group) for group in groups) / len(groups)


def _is_abstention(answer: str, citation_count: int) -> bool:
    explicit = ("insufficient_context", "no-answer", "无法回答")
    if any(marker in answer for marker in explicit):
        return True
    return citation_count == 0 and any(
        marker in answer for marker in ABSTENTION_MARKERS
    )


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload.get("cases", [])) != 60:
        raise ValueError("rag_eval_v1_must_contain_60_cases")
    return payload


def _compare(report: dict[str, Any], baseline_path: Path) -> dict[str, Any]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    for key in ("dataset_sha256", "knowledge_bundle_sha256"):
        if baseline.get(key) != report.get(key):
            raise ValueError(f"baseline_{key}_mismatch")
    deltas: dict[str, float] = {}
    for name, value in report["metrics"].items():
        before = baseline.get("metrics", {}).get(name)
        if isinstance(value, int | float) and isinstance(before, int | float):
            deltas[name] = round(value - before, 6)
    return {
        "baseline": str(baseline_path),
        "baseline_config": baseline.get("rag_config"),
        "deltas": deltas,
    }


def run(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    dataset = _load_dataset(args.dataset)
    config = RAG_CONFIGS[args.config]
    settings = get_settings()
    if args.mode == "mock" and settings.agent_provider != "mock":
        raise RuntimeError("mock_mode_requires_AGENT_PROVIDER=mock")
    if args.mode == "real":
        if settings.agent_provider == "mock":
            raise RuntimeError("real_mode_requires_external_AGENT_PROVIDER")
        if not args.execute:
            raise RuntimeError("real_mode_requires_--execute")
        if args.output.exists():
            raise RuntimeError("real_report_already_exists_refusing_overwrite")

    started = time.perf_counter()
    answerable = [case for case in dataset["cases"] if not case["should_abstain"]]
    abstention_cases = [case for case in dataset["cases"] if case["should_abstain"]]
    recalls: dict[int, list[float]] = {1: [], 3: [], 5: []}
    precisions: dict[int, list[float]] = {1: [], 3: [], 5: []}
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    retrieval_latencies: list[int] = []
    retrieval_abstentions: list[float] = []
    case_results: list[dict[str, Any]] = []
    generation_latencies: list[int] = []
    total_latencies: list[int] = []
    groundedness: list[float] = []
    relevance: list[float] = []
    citation_scores: list[float] = []
    abstention_hits: list[float] = []
    input_tokens = output_tokens = retries = 0
    estimated_cost = 0.0
    fallback_count = 0
    model_calls = 0

    with Session(engine) as db:
        ingest_builtin_knowledge(db)
        key_by_id = _document_keys(db)
        model_router = ModelRouter(db) if args.mode == "real" else None
        for case in dataset["cases"]:
            retrieval_started = time.perf_counter()
            chunks = retrieve(
                db,
                case["question"],
                limit=max(5, config["top_k"]),
                minimum_score=config["minimum_score"],
                rerank=config["rerank"],
            )
            retrieval_ms = int((time.perf_counter() - retrieval_started) * 1000)
            retrieval_latencies.append(retrieval_ms)
            ranked = _ranked_keys(chunks, key_by_id)
            relevant = set(case["expected_document_ids"])
            if relevant:
                for k in (1, 3, 5):
                    recalls[k].append(_recall_at(ranked, relevant, k))
                    precisions[k].append(_precision_at(ranked, relevant, k))
                reciprocal_ranks.append(_reciprocal_rank(ranked, relevant))
                ndcgs.append(_ndcg_at(ranked, relevant, 5))
            else:
                retrieval_abstentions.append(float(not ranked))
            result: dict[str, Any] = {
                "id": case["id"],
                "should_abstain": case["should_abstain"],
                "expected_document_ids": case["expected_document_ids"],
                "retrieved": [
                    {
                        "document_id": key_by_id.get(chunk.document_id),
                        "rank": index,
                        "score": chunk.score,
                    }
                    for index, chunk in enumerate(chunks, start=1)
                ],
                "retrieval_latency_ms": retrieval_ms,
            }
            if model_router is not None:
                generation_started = time.perf_counter()
                generated = run_knowledge(
                    db,
                    model_router,
                    case["question"],
                    chunks_override=chunks[: config["top_k"]],
                )
                generation_ms = int((time.perf_counter() - generation_started) * 1000)
                generation_latencies.append(generation_ms)
                total_latencies.append(retrieval_ms + generation_ms)
                invocation = generated.invocation
                input_tokens += invocation.input_tokens
                output_tokens += invocation.output_tokens
                retries += invocation.retries
                estimated_cost += invocation.estimated_cost_usd
                fallback_count += int(invocation.fallback_used)
                model_calls += int(invocation.error_code != "insufficient_context")
                citation_keys = [
                    key_by_id.get(citation.document_id, citation.document_id)
                    for citation in generated.citations
                ]
                abstained = _is_abstention(generated.answer, len(citation_keys))
                abstention_hits.append(float(abstained == case["should_abstain"]))
                if relevant:
                    groups = case["reference_terms"]
                    relevance_score = _reference_coverage(generated.answer, groups)
                    context_text = "\n".join(
                        chunk.text for chunk in chunks[: config["top_k"]]
                    )
                    grounded_score = _mean(
                        [
                            float(
                                any(term in generated.answer for term in group)
                                and any(term in context_text for term in group)
                            )
                            for group in groups
                        ]
                    )
                    citation_score = (
                        sum(key in relevant for key in citation_keys)
                        / len(citation_keys)
                        if citation_keys
                        else 0.0
                    )
                    relevance.append(relevance_score)
                    groundedness.append(grounded_score)
                    citation_scores.append(citation_score)
                result["generation"] = {
                    "answer": generated.answer,
                    "citations": citation_keys,
                    "abstained": abstained,
                    "latency_ms": generation_ms,
                    "input_tokens": invocation.input_tokens,
                    "output_tokens": invocation.output_tokens,
                    "estimated_cost_usd": invocation.estimated_cost_usd,
                    "fallback_used": invocation.fallback_used,
                    "error_code": invocation.error_code,
                }
            case_results.append(result)

    metrics: dict[str, Any] = {
        "recall_at_1": _mean(recalls[1]),
        "recall_at_3": _mean(recalls[3]),
        "recall_at_5": _mean(recalls[5]),
        "precision_at_1": _mean(precisions[1]),
        "precision_at_3": _mean(precisions[3]),
        "precision_at_5": _mean(precisions[5]),
        "mrr": _mean(reciprocal_ranks),
        "ndcg_at_5": _mean(ndcgs),
        "retrieval_abstention_rate": _mean(retrieval_abstentions),
        "retrieval_p50_ms": _percentile(retrieval_latencies, 0.50),
        "retrieval_p95_ms": _percentile(retrieval_latencies, 0.95),
    }
    if args.mode == "real":
        metrics.update(
            {
                "groundedness": _mean(groundedness),
                "answer_relevance": _mean(relevance),
                "citation_correctness": _mean(citation_scores),
                "abstention_accuracy": _mean(abstention_hits),
                "generation_p50_ms": _percentile(generation_latencies, 0.50),
                "generation_p95_ms": _percentile(generation_latencies, 0.95),
                "agent_total_p50_ms": _percentile(total_latencies, 0.50),
                "agent_total_p95_ms": _percentile(total_latencies, 0.95),
            }
        )
    else:
        metrics["generation_evaluation"] = "SKIPPED_REAL_MODEL"

    gate_names = ["recall_at_1", "recall_at_3", "recall_at_5", "mrr"]
    if args.mode == "real":
        gate_names.extend(
            [
                "groundedness",
                "answer_relevance",
                "citation_correctness",
                "abstention_accuracy",
            ]
        )
    gates = {
        name: {
            "value": metrics[name],
            "threshold": THRESHOLDS[name],
            "passed": metrics[name] >= THRESHOLDS[name],
        }
        for name in gate_names
    }
    report: dict[str, Any] = {
        "schema_version": "journey-rag-eval-report-1",
        "scoring_version": SCORING_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "execution_mode": args.mode,
        "dataset_version": dataset["dataset_version"],
        "dataset_size": len(dataset["cases"]),
        "answerable_cases": len(answerable),
        "abstention_cases": len(abstention_cases),
        "dataset_sha256": _sha256(args.dataset),
        "knowledge_bundle_version": dataset["knowledge_bundle_version"],
        "knowledge_bundle_sha256": _sha256(BUNDLE_PATH),
        "embedding_version": EMBEDDING_VERSION,
        "retriever_version": RETRIEVER_VERSION,
        "rag_config": {"name": args.config, **config, "evaluation_depth": 5},
        "provider": settings.agent_provider if args.mode == "real" else "mock",
        "model": settings.agent_model_map.get(
            "knowledge_answer", settings.agent_default_model
        ),
        "metrics": metrics,
        "gates": gates,
        "usage": {
            "calls": model_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "retries": retries,
            "fallback_count": fallback_count,
            "estimated_cost_usd": round(estimated_cost, 8),
        },
        "scoring_notes": {
            "groundedness": (
                "deterministic reference-point coverage in both answer and retrieved context; "
                "not hidden chain-of-thought or an LLM judge"
            ),
            "mock": (
                "Mock mode evaluates retrieval only; generation metrics are never reported "
                "as real-model quality"
            ),
        },
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "cases": case_results,
    }
    if args.baseline:
        report["comparison"] = _compare(report, args.baseline)
    return report, all(item["passed"] for item in gates.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--config", choices=sorted(RAG_CONFIGS), default="rag-v1")
    parser.add_argument("--mode", choices=("mock", "real"), default="mock")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    report, passed = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, gate in report["gates"].items():
        print(
            f"{'PASS' if gate['passed'] else 'FAIL'} {name}={gate['value']:.4f} "
            f"threshold={gate['threshold']:.4f}"
        )
    print(
        f"mode={report['execution_mode']} provider={report['provider']} model={report['model']} "
        f"dataset={report['dataset_size']} report={args.output}"
    )
    return 1 if args.enforce and not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
