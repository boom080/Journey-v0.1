"""Seal and verify the user-attested food scale-reference holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CANDIDATE_ROOT = ROOT.parent / "food_image_scale_candidate"
CANDIDATE_MANIFEST = CANDIDATE_ROOT / "pairs_manifest.jsonl"
ASSETS = ROOT / "assets"
MANIFEST = ROOT / "manifest.jsonl"
DATASET_VERSION = "journey-food-image-scale-holdout-v1"
SEALED_ON = "2026-07-29"
EXPECTED_PAIRS = 30
EXPECTED_IMAGES = 60


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_dimensions(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("expected PNG input")
    return struct.unpack(">II", data[16:24])


def seal() -> None:
    candidates = read_jsonl(CANDIDATE_MANIFEST)
    if len(candidates) != EXPECTED_PAIRS:
        raise RuntimeError(
            f"expected {EXPECTED_PAIRS} candidate pairs, found {len(candidates)}"
        )

    sealed: list[dict[str, Any]] = []
    for candidate in candidates:
        qa = candidate.get("visual_qa") or {}
        if qa.get("status") != "passed_contact_sheets_and_spot_checks":
            raise RuntimeError(f"candidate QA is incomplete: {candidate['id']}")
        if candidate["gold_mass_g"] is None:
            raise RuntimeError(f"candidate has no verified mass: {candidate['id']}")

        variants: dict[str, dict[str, Any]] = {}
        for variant, reference_type in (
            ("with_ruler", "centimeter_ruler"),
            ("without_ruler", "none"),
        ):
            source = CANDIDATE_ROOT / candidate[variant]["local_path"]
            destination = ASSETS / variant / f"{candidate['source_panel_id']}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            data = destination.read_bytes()
            width, height = png_dimensions(data)
            variants[variant] = {
                "local_path": f"assets/{variant}/{destination.name}",
                "sha256": sha256(data),
                "byte_length": len(data),
                "media_type": "image/png",
                "width": width,
                "height": height,
                "scale_reference": {
                    "type": reference_type,
                    "visible": variant == "with_ruler",
                    "public_api_supported": reference_type == "none",
                },
            }

        sealed.append(
            {
                "dataset_version": DATASET_VERSION,
                "sealed": True,
                "sealed_on": SEALED_ON,
                "id": candidate["id"],
                "source_panel_id": candidate["source_panel_id"],
                "category": candidate["category"],
                "gold": {
                    "food_name_zh": candidate["declared"]["food_name_zh"],
                    "mass_g": candidate["gold_mass_g"],
                    "measurement": candidate["measurement"],
                },
                "authorization": candidate["authorization"],
                "visual_qa": qa,
                "with_ruler": variants["with_ruler"],
                "without_ruler": variants["without_ruler"],
                "prompt_tuning_allowed": False,
                "evaluation_status": ("blocked_public_contract_lacks_centimeter_ruler"),
                "hard_gate_eligible": False,
                "hard_gate_blockers": [
                    "public_api_scale_reference_type_lacks_centimeter_ruler",
                    "real_provider_paired_evaluation_pending",
                ],
                "provenance_limitation": candidate["provenance_limitation"],
            }
        )

    write_jsonl(MANIFEST, sealed)
    verify()


def verify() -> None:
    entries = read_jsonl(MANIFEST)
    if len(entries) != EXPECTED_PAIRS:
        raise RuntimeError(f"expected {EXPECTED_PAIRS} pairs, found {len(entries)}")
    if len({entry["id"] for entry in entries}) != len(entries):
        raise RuntimeError("duplicate pair IDs")

    image_hashes: set[str] = set()
    image_count = 0
    for entry in entries:
        if entry["dataset_version"] != DATASET_VERSION or not entry["sealed"]:
            raise RuntimeError(f"entry is not sealed: {entry['id']}")
        if entry["authorization"]["status"] != "user_attested_final":
            raise RuntimeError(f"unexpected authorization: {entry['id']}")
        if entry["prompt_tuning_allowed"]:
            raise RuntimeError(f"sealed entry allows prompt tuning: {entry['id']}")
        if entry["gold"]["mass_g"] is None:
            raise RuntimeError(f"missing gold mass: {entry['id']}")
        if entry["visual_qa"]["status"] != "passed_contact_sheets_and_spot_checks":
            raise RuntimeError(f"visual QA not passed: {entry['id']}")
        if entry["hard_gate_eligible"]:
            raise RuntimeError(f"contract-blocked entry marked eligible: {entry['id']}")

        pair_hashes: list[str] = []
        for variant, expected_reference in (
            ("with_ruler", "centimeter_ruler"),
            ("without_ruler", "none"),
        ):
            record = entry[variant]
            data = (ROOT / record["local_path"]).read_bytes()
            digest = sha256(data)
            if digest != record["sha256"]:
                raise RuntimeError(f"asset hash mismatch: {entry['id']} {variant}")
            if png_dimensions(data) != (record["width"], record["height"]):
                raise RuntimeError(f"asset dimensions changed: {entry['id']} {variant}")
            if record["scale_reference"]["type"] != expected_reference:
                raise RuntimeError(f"reference mismatch: {entry['id']} {variant}")
            image_hashes.add(digest)
            pair_hashes.append(digest)
            image_count += 1
        if pair_hashes[0] == pair_hashes[1]:
            raise RuntimeError(f"pair variants are identical: {entry['id']}")

    if image_count != EXPECTED_IMAGES:
        raise RuntimeError(f"expected {EXPECTED_IMAGES} images, found {image_count}")
    if len(image_hashes) != EXPECTED_IMAGES:
        raise RuntimeError("duplicate sealed image content")

    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "status": "sealed_internal_evaluation_contract_blocked",
                "pairs": len(entries),
                "images": image_count,
                "gold_mass_complete": True,
                "visual_qa": "passed",
                "prompt_tuning_allowed": False,
                "hard_gate_eligible": 0,
                "provider_calls": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("seal", "verify"))
    args = parser.parse_args()
    try:
        {"seal": seal, "verify": verify}[args.command]()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"food-image scale holdout error: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
