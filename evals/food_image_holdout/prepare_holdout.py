"""Curate and verify the sealed Stage 9 food-image generalization holdout.

This set is intentionally separate from the 100-sample prompt-tuning manifest.
It contains no declared scale reference; it can detect prompt overfitting but
cannot prove the benefit of the new Journey scale-card flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from evals.food_image_real import prepare_dataset as source  # noqa: E402

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.jsonl"
ASSETS = ROOT / "assets"
CALIBRATION_MANIFEST = ROOT.parent / "food_image_real" / "manifest.jsonl"
DATASET_VERSION = "journey-food-image-holdout-v1"
EXPECTED_SAMPLES = 30


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def calibration_keys() -> tuple[set[str], set[str], set[str]]:
    entries = read_jsonl(CALIBRATION_MANIFEST)
    return (
        {entry["id"] for entry in entries},
        {entry["source"]["source_id"] for entry in entries},
        {entry["sha256"] for entry in entries},
    )


def spread(pool: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if len(pool) < count:
        raise RuntimeError(f"holdout pool has {len(pool)} records; {count} required")
    return [pool[(index * len(pool)) // count] for index in range(count)]


def choose_records(
    records: list[dict[str, Any]],
    available: set[str],
    excluded_source_ids: set[str],
) -> list[tuple[str, dict[str, Any]]]:
    usable = sorted(
        (
            record
            for record in records
            if record["dish_id"] in available
            and record["dish_id"] not in excluded_source_ids
            and 15 <= record["total_mass"] <= 1500
            and 0 < record["total_calories"] <= 3000
        ),
        key=lambda record: record["dish_id"],
    )
    singles = [record for record in usable if len(record["ingredients"]) == 1]
    selected_singles = spread(singles, 15)
    selected_ids = {record["dish_id"] for record in selected_singles}
    mixed = [
        record
        for record in usable
        if record["dish_id"] not in selected_ids
        and 2 <= len(record["ingredients"]) <= 8
        and len(source.meaningful_ingredients(record)) >= 2
    ]
    return [
        *(("single_food", record) for record in selected_singles),
        *(("mixed_meal", record) for record in spread(mixed, 15)),
    ]


def asset_metadata(data: bytes, relative_path: str) -> dict[str, Any]:
    media_type, width, height = source.image_metadata(data)
    return {
        "local_path": relative_path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "media_type": media_type,
        "width": width,
        "height": height,
    }


def entry_for(
    *,
    category: str,
    index: int,
    record: dict[str, Any],
    image_url: str,
    data: bytes,
) -> dict[str, Any]:
    dish_id = record["dish_id"]
    ranked = source.meaningful_ingredients(record)
    relative_path = f"assets/nutrition5k/{dish_id}.png"
    return {
        "dataset_version": DATASET_VERSION,
        "id": f"holdout-{category.replace('_', '-')}-{index:03d}",
        "category": category,
        "holdout_role": "sealed_generalization_no_reference",
        "source": {
            "dataset": "Nutrition5k",
            "source_id": dish_id,
            "source_page": source.N5K_SOURCE_PAGE,
            "image_url": image_url,
            "license": "CC BY 4.0",
            "license_url": source.N5K_LICENSE,
            "attribution": "Thames et al., Nutrition5k, CVPR 2021",
        },
        **asset_metadata(data, relative_path),
        "scale_reference": {
            "type": "none",
            "size_cm": None,
            "visible": False,
        },
        "gold": {
            "is_food": True,
            "names": [
                {
                    "canonical_en": item["name"],
                    "aliases": source.aliases(item["name"]),
                }
                for item in ranked[:3]
            ],
            "total_mass_g": round(record["total_mass"], 3),
            "total_calories_kcal": round(record["total_calories"], 3),
            "should_abstain": False,
            "top3_metric_eligible": True,
            "portion_metric_eligible": category == "single_food",
            "calorie_metric_eligible": True,
            "scale_reference_expected_used": False,
            "difficulty_tags": ["sealed_holdout", "no_explicit_scale"],
        },
    }


def curate() -> None:
    _, excluded_source_ids, excluded_hashes = calibration_keys()
    rgb = source.list_n5k_rgb()
    records = source.load_n5k_metadata()
    selected = choose_records(records, set(rgb), excluded_source_ids)
    entries = []
    counters = {"single_food": 0, "mixed_meal": 0}
    for category, record in selected:
        counters[category] += 1
        image_url = rgb[record["dish_id"]]["url"]
        data = source.request_bytes(image_url)
        entry = entry_for(
            category=category,
            index=counters[category],
            record=record,
            image_url=image_url,
            data=data,
        )
        if entry["sha256"] in excluded_hashes:
            raise RuntimeError(f"holdout hash overlaps calibration set: {entry['id']}")
        path = ROOT / entry["local_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entries.append(entry)
    MANIFEST.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )
    verify()


def download() -> None:
    for entry in read_jsonl(MANIFEST):
        path = ROOT / entry["local_path"]
        if (
            path.exists()
            and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        ):
            continue
        data = source.request_bytes(entry["source"]["image_url"])
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"download hash mismatch: {entry['id']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    verify()


def verify() -> None:
    entries = read_jsonl(MANIFEST)
    calibration_ids, calibration_source_ids, calibration_hashes = calibration_keys()
    if len(entries) != EXPECTED_SAMPLES:
        raise RuntimeError(
            f"expected {EXPECTED_SAMPLES} holdout samples, found {len(entries)}"
        )
    ids = [entry["id"] for entry in entries]
    source_ids = [entry["source"]["source_id"] for entry in entries]
    hashes = [entry["sha256"] for entry in entries]
    if len(ids) != len(set(ids)) or len(source_ids) != len(set(source_ids)):
        raise RuntimeError("holdout IDs and source IDs must be unique")
    if set(ids) & calibration_ids:
        raise RuntimeError("holdout sample ID overlaps calibration set")
    if set(source_ids) & calibration_source_ids:
        raise RuntimeError("holdout source ID overlaps calibration set")
    if set(hashes) & calibration_hashes:
        raise RuntimeError("holdout image hash overlaps calibration set")
    total_bytes = 0
    categories: dict[str, int] = {}
    for entry in entries:
        if entry["dataset_version"] != DATASET_VERSION:
            raise RuntimeError(f"wrong dataset version: {entry['id']}")
        if entry.get("holdout_role") != "sealed_generalization_no_reference":
            raise RuntimeError(f"holdout role is not sealed: {entry['id']}")
        if (entry.get("scale_reference") or {}).get("type") != "none":
            raise RuntimeError(
                f"generalization holdout must not claim a scale reference: {entry['id']}"
            )
        path = ROOT / entry["local_path"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"asset hash mismatch: {entry['id']}")
        media_type, width, height = source.image_metadata(data)
        if (media_type, width, height) != (
            entry["media_type"],
            entry["width"],
            entry["height"],
        ):
            raise RuntimeError(f"asset metadata mismatch: {entry['id']}")
        total_bytes += len(data)
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1
    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "samples": len(entries),
                "categories": categories,
                "assets_bytes": total_bytes,
                "calibration_overlap": {
                    "sample_ids": 0,
                    "source_ids": 0,
                    "sha256": 0,
                },
                "scale_reference_cohort": "pending",
                "status": "verified_generalization_only",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("curate", "download", "verify"))
    args = parser.parse_args()
    try:
        {"curate": curate, "download": download, "verify": verify}[args.command]()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"food-image holdout error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
