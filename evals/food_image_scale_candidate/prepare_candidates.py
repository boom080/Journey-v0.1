"""Prepare and verify user-attested Xiaohongshu food-weight candidates.

This is deliberately a candidate dataset, not a sealed evaluation cohort.
Cropping preserves the pixels and visible evidence. Labels, scale readouts,
permission provenance, and answer-redacted paired inputs still require review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SOURCES = ASSETS / "source"
PANELS = ASSETS / "panels"
SOURCE_MANIFEST = ROOT / "source_manifest.jsonl"
PANEL_MANIFEST = ROOT / "manifest.jsonl"
PAIR_MANIFEST = ROOT / "pairs_manifest.jsonl"
PAIR_SCRIPT = ROOT / "make_redacted_pairs.swift"
DATASET_VERSION = "journey-food-image-scale-candidate-v0"
ATTESTED_ON = "2026-07-29"
EXPECTED_SOURCES = 16
EXPECTED_PANELS = 88
EXPECTED_SCALE_PAIR_CANDIDATES = 30
EXPECTED_PAIR_IMAGES = 60


def labels(names: list[str], masses: list[float | None]) -> list[dict[str, Any]]:
    if len(names) != len(masses):
        raise ValueError("name and mass counts differ")
    return [
        {"food_name_zh": name, "declared_mass_g": mass}
        for name, mass in zip(names, masses)
    ]


SOURCE_SPECS: list[dict[str, Any]] = [
    {
        "id": "xhs-001",
        "role": "portion_reference_only",
        "layout": None,
        "labels": [],
        "notes": "长图参考；无逐格秤读数，不进入称重候选。",
    },
    {
        "id": "xhs-002",
        "role": "weighed_reference_candidate",
        "layout": [3, 3],
        "labels": labels(
            [
                "西兰花",
                "绿豆芽",
                "芹菜",
                "洋葱",
                "胡萝卜",
                "空心菜",
                "豌豆",
                "莲藕",
                "西芹",
            ],
            [100] * 9,
        ),
    },
    {
        "id": "xhs-003",
        "role": "weighed_reference_candidate",
        "layout": [3, 3],
        "labels": labels(
            [
                "豆腐干",
                "千张",
                "素鸡",
                "老豆腐",
                "内脂豆腐",
                "嫩豆腐",
                "鸡肉",
                "蒜苔",
                "卷心菜",
            ],
            [100] * 9,
        ),
    },
    {
        "id": "xhs-004",
        "role": "weighed_reference_candidate",
        "layout": [3, 3],
        "labels": labels(
            ["丝瓜", "土豆", "豇豆", "茄子", "木耳", "花菜", "番茄", "紫薯", "红苋菜"],
            [100] * 9,
        ),
    },
    {
        "id": "xhs-005",
        "role": "weighed_reference_candidate",
        "layout": [3, 3],
        "labels": labels(
            [
                "猪里脊",
                "红椒",
                "秋葵",
                "小香干",
                "黄瓜",
                "四季豆",
                "韭黄",
                "竹笋",
                "韭菜",
            ],
            [100] * 9,
        ),
    },
    {
        "id": "xhs-006",
        "role": "weighed_reference_candidate",
        "layout": [3, 3],
        "labels": labels(
            [
                "基围虾",
                "牛肩肉",
                "贝贝南瓜",
                "芦笋",
                "大米",
                "南瓜",
                "生菜",
                "莴笋",
                "青椒",
            ],
            [100] * 9,
        ),
    },
    {
        "id": "xhs-007",
        "role": "excluded_duplicate_montage",
        "layout": None,
        "labels": [],
        "notes": "对 xhs-002 至 xhs-005 的低分辨率总览，不重复拆分。",
    },
    {
        "id": "xhs-008",
        "role": "scale_pair_candidate",
        "layout": [3, 2],
        "labels": labels(
            ["鸡翅尖", "牛肉", "鸡翅尖", "牛肉", "鸡翅尖", "牛肉"],
            [10, 10, 20, 20, 50, 50],
        ),
    },
    {
        "id": "xhs-009",
        "role": "scale_pair_candidate",
        "layout": [3, 2],
        "labels": labels(
            ["猪排骨", "鸡胸肉", "猪排骨", "鸡胸肉", "猪排骨", "鸡胸肉"],
            [10, 10, 20, 20, 50, 50],
        ),
    },
    {
        "id": "xhs-010",
        "role": "scale_pair_candidate",
        "layout": [3, 2],
        "labels": labels(
            ["虾皮", "鲜虾仁", "虾皮", "鲜虾仁", "虾皮", "鲜虾仁"],
            [2, 10, 5, 30, 10, 50],
        ),
    },
    {
        "id": "xhs-011",
        "role": "scale_pair_candidate",
        "layout": [3, 2],
        "labels": labels(
            ["鸭胗", "猪里脊", "鸭胗", "猪里脊", "鸭胗", "猪里脊"],
            [10, 10, 20, 20, 50, 50],
        ),
    },
    {
        "id": "xhs-012",
        "role": "scale_pair_candidate",
        "layout": [3, 2],
        "labels": labels(
            ["猪五花", "猪肝", "猪五花", "猪肝", "猪五花", "猪肝"],
            [10, 10, 20, 20, 30, 50],
        ),
    },
    {
        "id": "xhs-013",
        "role": "weighed_reference_candidate",
        "layout": [2, 2],
        "labels": labels(["煮鸡蛋", "苏打饼干", "饺子", "米饭"], [50, 7, 30, 108]),
        "notes": "部分叠字为单个/单片参考，与画面数量或秤读数可能不同，必须人工复核。",
    },
    {
        "id": "xhs-014",
        "role": "weighed_reference_candidate",
        "layout": [2, 2],
        "labels": labels(["红枣", "橙柚", "开心果", "小黄瓜"], [2, 280, 1, 110]),
        "notes": "部分叠字为单颗/单个参考，与画面数量或秤读数可能不同，必须人工复核。",
    },
    {
        "id": "xhs-015",
        "role": "portion_reference_only",
        "layout": [1, 1],
        "labels": labels(["黑咖啡粉"], [3]),
        "notes": "勺子未放在秤上且显示为零，不作为称重金标。",
    },
    {
        "id": "xhs-016",
        "role": "weighed_reference_candidate",
        "layout": [2, 2],
        "labels": labels(["茄子", "圣女果", "黄瓜", "洋葱"], [200, 200, 200, 200]),
        "notes": "画面另含整只/颗数等经验说明；只转录秤上样本的 200g 声明。",
    },
]

SCALE_READOUTS_G = {
    "xhs-008-p01": 10.0,
    "xhs-008-p02": 10.0,
    "xhs-008-p03": 20.2,
    "xhs-008-p04": 20.0,
    "xhs-008-p05": 49.8,
    "xhs-008-p06": 50.1,
    "xhs-009-p01": 10.3,
    "xhs-009-p02": 9.8,
    "xhs-009-p03": 20.2,
    "xhs-009-p04": 20.2,
    "xhs-009-p05": 50.0,
    "xhs-009-p06": 50.2,
    "xhs-010-p01": 2.0,
    "xhs-010-p02": 9.6,
    "xhs-010-p03": 5.0,
    "xhs-010-p04": 29.9,
    "xhs-010-p05": 10.0,
    "xhs-010-p06": 50.0,
    "xhs-011-p01": 10.3,
    "xhs-011-p02": 10.3,
    "xhs-011-p03": 20.0,
    "xhs-011-p04": 20.0,
    "xhs-011-p05": 50.3,
    "xhs-011-p06": 50.3,
    "xhs-012-p01": 10.0,
    "xhs-012-p02": 9.9,
    "xhs-012-p03": 20.2,
    "xhs-012-p04": 20.2,
    "xhs-012-p05": 30.0,
    "xhs-012-p06": 50.3,
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_dimensions(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("expected PNG input")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def crop_panel(source: Path, destination: Path, box: dict[str, int]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # sips treats a zero crop coordinate as a default rather than a literal
    # top/left edge in some grid positions. One-pixel safe offsets keep every
    # cell unambiguous while changing only the outermost border.
    offset_y = max(1, box["y"])
    offset_x = max(1, box["x"])
    result = subprocess.run(
        [
            "sips",
            "-c",
            str(box["height"]),
            str(box["width"]),
            "--cropOffset",
            str(offset_y),
            str(offset_x),
            str(source),
            "-o",
            str(destination),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"sips crop failed for {source.name}: {result.stderr.strip()}"
        )


def authorization() -> dict[str, Any]:
    return {
        "status": "user_attested_final",
        "attested_on": ATTESTED_ON,
        "scope": "Journey project processing and use",
        "source_url": None,
        "evidence_path": None,
        "provenance_verification": "unavailable_user_closed_posts",
        "distribution": "internal_project_only_no_dataset_redistribution",
    }


def prepare() -> None:
    if shutil.which("sips") is None:
        raise RuntimeError("macOS sips is required for deterministic local cropping")
    source_entries: list[dict[str, Any]] = []
    panel_entries: list[dict[str, Any]] = []
    for spec in SOURCE_SPECS:
        source_path = SOURCES / f"{spec['id']}.png"
        if not source_path.exists():
            raise RuntimeError(f"missing source asset: {source_path}")
        source_data = source_path.read_bytes()
        width, height = png_dimensions(source_data)
        source_entries.append(
            {
                "dataset_version": DATASET_VERSION,
                "id": spec["id"],
                "platform": "xiaohongshu",
                "role": spec["role"],
                "local_path": f"assets/source/{spec['id']}.png",
                "sha256": sha256(source_data),
                "byte_length": len(source_data),
                "media_type": "image/png",
                "width": width,
                "height": height,
                "authorization": authorization(),
                "notes": spec.get("notes"),
            }
        )
        layout = spec["layout"]
        if layout is None:
            continue
        rows, columns = layout
        panel_width = width // columns
        panel_height = height // rows
        if len(spec["labels"]) != rows * columns:
            raise RuntimeError(f"label count does not match grid: {spec['id']}")
        for index, label in enumerate(spec["labels"], start=1):
            row = (index - 1) // columns
            column = (index - 1) % columns
            box = {
                "x": column * panel_width,
                "y": row * panel_height,
                "width": panel_width,
                "height": panel_height,
            }
            panel_id = f"{spec['id']}-p{index:02d}"
            panel_path = PANELS / f"{panel_id}.png"
            if rows == 1 and columns == 1:
                panel_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, panel_path)
            else:
                crop_panel(source_path, panel_path, box)
            panel_data = panel_path.read_bytes()
            actual_width, actual_height = png_dimensions(panel_data)
            scale_pair = spec["role"] == "scale_pair_candidate"
            readout = SCALE_READOUTS_G.get(panel_id)
            hard_gate_blockers = ["answer_text_and_scale_display_redaction_pending"]
            if not scale_pair:
                hard_gate_blockers.append("known_dimension_reference_missing")
            panel_entries.append(
                {
                    "dataset_version": DATASET_VERSION,
                    "id": panel_id,
                    "source_id": spec["id"],
                    "role": spec["role"],
                    "category": "single_food",
                    "local_path": f"assets/panels/{panel_id}.png",
                    "sha256": sha256(panel_data),
                    "byte_length": len(panel_data),
                    "media_type": "image/png",
                    "width": actual_width,
                    "height": actual_height,
                    "crop_box": box,
                    "declared": label,
                    "gold_mass_g": readout,
                    "measurement": {
                        "scale_readout_g": readout,
                        "verification": (
                            "manual_contact_sheet_and_source_panel"
                            if readout is not None
                            else "not_verified"
                        ),
                        "verified_on": ATTESTED_ON if readout is not None else None,
                    },
                    "evidence": {
                        "food_visible": True,
                        "scale_display_visible": spec["role"]
                        != "portion_reference_only",
                        "ruler_visible": scale_pair,
                        "answer_text_visible": True,
                        "watermark_or_creator_mark_visible": spec["id"]
                        not in {"xhs-008", "xhs-009", "xhs-010", "xhs-011", "xhs-012"},
                    },
                    "authorization": authorization(),
                    "hard_gate_eligible": False,
                    "hard_gate_blockers": hard_gate_blockers,
                    "notes": spec.get("notes"),
                }
            )
    write_jsonl(SOURCE_MANIFEST, source_entries)
    write_jsonl(PANEL_MANIFEST, panel_entries)
    verify()


def make_pairs() -> None:
    if shutil.which("swift") is None:
        raise RuntimeError("Swift is required for deterministic answer redaction")
    entries = read_jsonl(PANEL_MANIFEST)
    pair_entries: list[dict[str, Any]] = []
    for entry in entries:
        if entry["role"] != "scale_pair_candidate":
            continue
        source_path = ROOT / entry["local_path"]
        pair_id = entry["id"]
        with_path = ASSETS / "pairs" / "with_ruler" / f"{pair_id}.png"
        without_path = ASSETS / "pairs" / "without_ruler" / f"{pair_id}.png"
        with_path.parent.mkdir(parents=True, exist_ok=True)
        without_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "swift",
                str(PAIR_SCRIPT),
                str(source_path),
                str(with_path),
                str(without_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"pair redaction failed for {pair_id}: {result.stderr.strip()}"
            )
        with_data = with_path.read_bytes()
        without_data = without_path.read_bytes()
        with_width, with_height = png_dimensions(with_data)
        without_width, without_height = png_dimensions(without_data)
        if (with_width, with_height) != (entry["width"], entry["height"]):
            raise RuntimeError(f"with-ruler dimensions changed: {pair_id}")
        if (without_width, without_height) != (entry["width"], entry["height"]):
            raise RuntimeError(f"without-ruler dimensions changed: {pair_id}")
        pair_entries.append(
            {
                "dataset_version": DATASET_VERSION,
                "id": f"pair-{pair_id}",
                "source_panel_id": pair_id,
                "category": entry["category"],
                "declared": entry["declared"],
                "gold_mass_g": entry["gold_mass_g"],
                "measurement": entry["measurement"],
                "authorization": authorization(),
                "with_ruler": {
                    "local_path": f"assets/pairs/with_ruler/{pair_id}.png",
                    "sha256": sha256(with_data),
                    "byte_length": len(with_data),
                    "width": with_width,
                    "height": with_height,
                    "answer_text_visible": False,
                    "scale_display_visible": False,
                    "ruler_visible": True,
                },
                "without_ruler": {
                    "local_path": f"assets/pairs/without_ruler/{pair_id}.png",
                    "sha256": sha256(without_data),
                    "byte_length": len(without_data),
                    "width": without_width,
                    "height": without_height,
                    "answer_text_visible": False,
                    "scale_display_visible": False,
                    "ruler_visible": False,
                },
                "redaction": {
                    "method": "deterministic_solid_masks_no_generation",
                    "answer_text_rect_top_left": [320, 0, 220, 190],
                    "scale_display_rect_top_left": [135, 365, 190, 115],
                    "ruler_rect_top_left_without_only": [360, 120, 140, 360],
                },
                "visual_qa": {
                    "status": "passed_contact_sheets_and_spot_checks",
                    "checked_on": ATTESTED_ON,
                    "food_obscured": False,
                    "answer_leakage_observed": False,
                },
                "hard_gate_eligible": False,
                "hard_gate_blockers": ["sealed_dataset_version_pending"],
                "provenance_limitation": "source links unavailable; permission retained as user attestation",
            }
        )
    write_jsonl(PAIR_MANIFEST, pair_entries)
    verify_pairs()


def verify() -> None:
    source_entries = read_jsonl(SOURCE_MANIFEST)
    panel_entries = read_jsonl(PANEL_MANIFEST)
    if len(source_entries) != EXPECTED_SOURCES:
        raise RuntimeError(
            f"expected {EXPECTED_SOURCES} sources, found {len(source_entries)}"
        )
    if len(panel_entries) != EXPECTED_PANELS:
        raise RuntimeError(
            f"expected {EXPECTED_PANELS} panels, found {len(panel_entries)}"
        )
    if len({entry["id"] for entry in source_entries}) != len(source_entries):
        raise RuntimeError("duplicate source IDs")
    if len({entry["id"] for entry in panel_entries}) != len(panel_entries):
        raise RuntimeError("duplicate panel IDs")
    scale_pair_count = sum(
        entry["role"] == "scale_pair_candidate" for entry in panel_entries
    )
    if scale_pair_count != EXPECTED_SCALE_PAIR_CANDIDATES:
        raise RuntimeError(
            f"expected {EXPECTED_SCALE_PAIR_CANDIDATES} scale candidates, found {scale_pair_count}"
        )
    scale_pairs = [
        entry for entry in panel_entries if entry["role"] == "scale_pair_candidate"
    ]
    if any(entry["gold_mass_g"] is None for entry in scale_pairs):
        raise RuntimeError("scale candidate is missing a verified scale readout")
    if len(SCALE_READOUTS_G) != EXPECTED_SCALE_PAIR_CANDIDATES:
        raise RuntimeError("scale readout map count does not match expected candidates")
    for entry in [*source_entries, *panel_entries]:
        path = ROOT / entry["local_path"]
        data = path.read_bytes()
        if sha256(data) != entry["sha256"]:
            raise RuntimeError(f"asset hash mismatch: {entry['id']}")
        width, height = png_dimensions(data)
        if (width, height) != (entry["width"], entry["height"]):
            raise RuntimeError(f"asset dimension mismatch: {entry['id']}")
        if entry["authorization"]["status"] != "user_attested_final":
            raise RuntimeError(f"unexpected authorization status: {entry['id']}")
    if any(entry["hard_gate_eligible"] for entry in panel_entries):
        raise RuntimeError("candidate dataset must not mark hard-gate eligibility")
    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "status": "verified_candidate_only",
                "sources": len(source_entries),
                "panels": len(panel_entries),
                "scale_pair_candidates": scale_pair_count,
                "excluded_duplicate_montages": sum(
                    entry["role"] == "excluded_duplicate_montage"
                    for entry in source_entries
                ),
                "hard_gate_eligible": 0,
                "authorization": "user_attested_final_source_links_unavailable",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def verify_pairs() -> None:
    entries = read_jsonl(PAIR_MANIFEST)
    if len(entries) != EXPECTED_SCALE_PAIR_CANDIDATES:
        raise RuntimeError(
            f"expected {EXPECTED_SCALE_PAIR_CANDIDATES} pairs, found {len(entries)}"
        )
    if len({entry["id"] for entry in entries}) != len(entries):
        raise RuntimeError("duplicate pair IDs")
    image_count = 0
    for entry in entries:
        if entry["authorization"]["status"] != "user_attested_final":
            raise RuntimeError(f"unexpected pair authorization: {entry['id']}")
        if entry["hard_gate_eligible"]:
            raise RuntimeError(
                f"unsealed pair marked hard-gate eligible: {entry['id']}"
            )
        if entry["gold_mass_g"] is None:
            raise RuntimeError(f"pair is missing verified scale mass: {entry['id']}")
        if entry["visual_qa"]["status"] != "passed_contact_sheets_and_spot_checks":
            raise RuntimeError(f"pair visual QA is not complete: {entry['id']}")
        if (
            entry["visual_qa"]["food_obscured"]
            or entry["visual_qa"]["answer_leakage_observed"]
        ):
            raise RuntimeError(f"pair visual QA failed: {entry['id']}")
        for variant, ruler_expected in (("with_ruler", True), ("without_ruler", False)):
            record = entry[variant]
            data = (ROOT / record["local_path"]).read_bytes()
            if sha256(data) != record["sha256"]:
                raise RuntimeError(f"pair hash mismatch: {entry['id']} {variant}")
            width, height = png_dimensions(data)
            if (width, height) != (record["width"], record["height"]):
                raise RuntimeError(f"pair dimensions changed: {entry['id']} {variant}")
            if record["answer_text_visible"] or record["scale_display_visible"]:
                raise RuntimeError(
                    f"answer leakage flag remains: {entry['id']} {variant}"
                )
            if record["ruler_visible"] != ruler_expected:
                raise RuntimeError(f"ruler flag mismatch: {entry['id']} {variant}")
            image_count += 1
    if image_count != EXPECTED_PAIR_IMAGES:
        raise RuntimeError(
            f"expected {EXPECTED_PAIR_IMAGES} pair images, found {image_count}"
        )
    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "status": "verified_redacted_pairs_qa_passed_unsealed",
                "pairs": len(entries),
                "images": image_count,
                "with_ruler": len(entries),
                "without_ruler": len(entries),
                "hard_gate_eligible": 0,
                "authorization": "user_attested_final_source_links_unavailable",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("prepare", "make-pairs", "verify", "verify-pairs")
    )
    args = parser.parse_args()
    try:
        {
            "prepare": prepare,
            "make-pairs": make_pairs,
            "verify": verify,
            "verify-pairs": verify_pairs,
        }[args.command]()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"food-image scale candidate error: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
