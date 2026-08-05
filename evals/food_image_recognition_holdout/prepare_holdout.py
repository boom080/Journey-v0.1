"""Curate, seal, and verify the ADR-031 recognition-only holdout.

The dataset uses Wikimedia Commons thumbnails from a source family that is not
present in the earlier Stage 9 manifests. Curation never calls a model. Visual
and privacy QA must be attested before the candidate manifest can be sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from evals.food_image_real import prepare_dataset as image_utils  # noqa: E402

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CANDIDATE_MANIFEST = ROOT / "candidate_manifest.jsonl"
MANIFEST = ROOT / "manifest.jsonl"
DATASET_VERSION = "journey-food-image-recognition-holdout-v2"
SEALED_ON = "2026-07-30"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "JourneyEvaluation/2.0 (local non-commercial quality evaluation)"
EXPECTED_COUNTS = {
    "chinese_home_meal": 20,
    "single_food": 15,
    "mixed_meal": 10,
    "packaged_food": 10,
    "nonfood": 5,
}
ALLOWED_LICENSES = {
    "CC BY 2.0",
    "CC BY 2.5",
    "CC BY 3.0",
    "CC BY 4.0",
    "CC BY-SA 2.0",
    "CC BY-SA 2.5",
    "CC BY-SA 3.0",
    "CC BY-SA 4.0",
    "CC0",
    "Public domain",
}
PUBLIC_DOMAIN_LICENSE_URL = "https://creativecommons.org/publicdomain/mark/1.0/"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_DATASET_BYTES = 60 * 1024 * 1024
MIN_DIMENSION = 240
_last_request_at = 0.0


def sample(
    cohort: str,
    index: int,
    query: str,
    canonical_en: str,
    *aliases: str,
    selection_rank: int = 0,
) -> dict[str, Any]:
    return {
        "id": f"recognition-{cohort.replace('_', '-')}-{index:03d}",
        "cohort": cohort,
        "query": query,
        "selection_rank": selection_rank,
        "names": [{"canonical_en": canonical_en, "aliases": list(aliases)}],
    }


SPECS = [
    sample("chinese_home_meal", 1, "mapo tofu", "mapo tofu", "麻婆豆腐"),
    sample(
        "chinese_home_meal",
        2,
        "stir fried tomatoes scrambled eggs",
        "tomato scrambled eggs",
        "番茄炒蛋",
        "西红柿炒鸡蛋",
    ),
    sample(
        "chinese_home_meal",
        3,
        "kung pao chicken",
        "kung pao chicken",
        "宫保鸡丁",
    ),
    sample(
        "chinese_home_meal", 4, "Chinese egg fried rice", "egg fried rice", "蛋炒饭"
    ),
    sample("chinese_home_meal", 5, "jiaozi dumplings", "jiaozi", "饺子"),
    sample("chinese_home_meal", 6, "baozi Chinese", "baozi", "包子"),
    sample("chinese_home_meal", 7, "Chinese rice congee", "rice congee", "粥", "白粥"),
    sample("chinese_home_meal", 8, "wonton soup", "wonton soup", "馄饨汤"),
    sample("chinese_home_meal", 9, "hot and sour soup", "hot and sour soup", "酸辣汤"),
    sample("chinese_home_meal", 10, "Chinese steamed fish", "steamed fish", "清蒸鱼"),
    sample("chinese_home_meal", 11, "red braised pork", "red braised pork", "红烧肉"),
    sample(
        "chinese_home_meal",
        12,
        "Chinese scallion pancake",
        "scallion pancake",
        "葱油饼",
    ),
    sample("chinese_home_meal", 13, "Chow mein plates", "chow mein", "炒面"),
    sample(
        "chinese_home_meal", 14, "Chinese eggplant dish", "Chinese eggplant", "茄子"
    ),
    sample(
        "chinese_home_meal",
        15,
        "sweet and sour pork",
        "sweet and sour pork",
        "糖醋里脊",
        "咕咾肉",
    ),
    sample(
        "chinese_home_meal",
        16,
        "twice cooked pork",
        "twice cooked pork",
        "回锅肉",
    ),
    sample("chinese_home_meal", 17, "Chinese braised tofu", "braised tofu", "红烧豆腐"),
    sample(
        "chinese_home_meal",
        18,
        "Chinese stir fried green vegetables",
        "stir-fried greens",
        "炒青菜",
    ),
    sample("chinese_home_meal", 19, "char siu rice", "char siu rice", "叉烧饭"),
    sample(
        "chinese_home_meal",
        20,
        "Chinese beef noodle soup",
        "beef noodle soup",
        "牛肉面",
    ),
    sample("single_food", 1, "red apple isolated photograph", "apple", "苹果"),
    sample("single_food", 2, "single banana fruit", "banana", "香蕉"),
    sample("single_food", 3, "single orange fruit", "orange", "橙子"),
    sample("single_food", 4, "grapes fruit bowl photograph", "grapes", "葡萄"),
    sample("single_food", 5, "Liat Portal Fresh Broccoli", "broccoli", "西兰花"),
    sample("single_food", 6, "Red tomatoes.jpg", "tomato", "番茄", "西红柿"),
    sample("single_food", 7, "Boiled Eggs.jpg", "boiled egg", "水煮蛋"),
    sample(
        "single_food",
        8,
        "uncooked stinky tofu",
        "stinky tofu",
        "tofu",
        "豆腐",
        "臭豆腐",
    ),
    sample("single_food", 9, "bowl of white rice", "white rice", "米饭"),
    sample("single_food", 10, "corn on the cob plate", "corn on the cob", "玉米"),
    sample(
        "single_food",
        11,
        "potatoes San Francisco farmers market",
        "potato",
        "土豆",
    ),
    sample(
        "single_food", 12, "cooked chicken breast plate", "chicken breast", "鸡胸肉"
    ),
    sample("single_food", 13, "cooked salmon fillet plate", "salmon", "三文鱼"),
    sample("single_food", 14, "plain yogurt bowl", "plain yogurt", "原味酸奶"),
    sample("single_food", 15, "glass of milk drink", "milk", "牛奶"),
    sample("mixed_meal", 1, "sushi platter", "sushi platter", "寿司拼盘"),
    sample("mixed_meal", 2, "Japanese curry rice", "curry rice", "咖喱饭"),
    sample("mixed_meal", 3, "salad bowl food photograph", "salad bowl", "沙拉"),
    sample("mixed_meal", 4, "breakfast plate meal", "breakfast plate", "早餐拼盘"),
    sample(
        "mixed_meal",
        5,
        "pasta with meat sauce plate",
        "pasta with meat sauce",
        "肉酱意面",
    ),
    sample("mixed_meal", 6, "pizza meal plate", "pizza", "披萨"),
    sample("mixed_meal", 7, "burrito bowl", "burrito bowl", "墨西哥卷饼碗"),
    sample("mixed_meal", 8, "sandwich plate meal", "sandwich", "三明治"),
    sample("mixed_meal", 9, "noodle soup bowl", "noodle soup", "汤面"),
    sample("mixed_meal", 10, "steak dinner plate", "steak dinner", "牛排餐"),
    sample(
        "packaged_food",
        1,
        "2 Litre carton skimmed milk",
        "packaged milk",
        "盒装牛奶",
    ),
    sample("packaged_food", 2, "breakfast cereal box", "breakfast cereal", "早餐谷物"),
    sample(
        "packaged_food",
        3,
        "instant noodles package",
        "instant noodles",
        "方便面",
    ),
    sample("packaged_food", 4, "yogurt cup package", "packaged yogurt", "杯装酸奶"),
    sample(
        "packaged_food",
        5,
        "chocolate bar wrapper",
        "chocolate bar",
        "巧克力",
    ),
    sample("packaged_food", 6, "can of baked beans", "canned beans", "豆罐头"),
    sample("packaged_food", 7, "potato chips bag", "potato chips", "薯片"),
    sample(
        "packaged_food",
        8,
        "packaged sliced bread loaf",
        "packaged bread",
        "包装面包",
    ),
    sample("packaged_food", 9, "bottled fruit juice", "fruit juice", "果汁"),
    sample("packaged_food", 10, "biscuit packet food", "biscuits", "饼干"),
    sample("nonfood", 1, "computer keyboard isolated", "", selection_rank=0),
    sample("nonfood", 2, "wooden chair photograph", "", selection_rank=0),
    sample("nonfood", 3, "bicycle isolated", "", selection_rank=0),
    sample("nonfood", 4, "running shoe isolated", "", selection_rank=0),
    sample("nonfood", 5, "headphones object photograph", "", selection_rank=0),
]
INITIAL_QA_REPLACEMENTS = [
    "recognition-chinese-home-meal-013",
    "recognition-single-food-001",
    "recognition-single-food-004",
    "recognition-single-food-005",
    "recognition-single-food-006",
    "recognition-single-food-008",
    "recognition-single-food-011",
    "recognition-single-food-015",
    "recognition-mixed-meal-003",
    "recognition-packaged-food-001",
    "recognition-packaged-food-006",
    "recognition-packaged-food-008",
    "recognition-packaged-food-010",
    "recognition-nonfood-002",
    "recognition-nonfood-005",
]
SECOND_QA_REPLACEMENTS = [
    "recognition-chinese-home-meal-013",
    "recognition-single-food-005",
    "recognition-single-food-008",
    "recognition-single-food-011",
    "recognition-packaged-food-001",
    "recognition-packaged-food-006",
]
THIRD_QA_REPLACEMENTS = [
    "recognition-single-food-006",
    "recognition-single-food-007",
]


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


def plain_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def request_json(params: dict[str, str]) -> dict[str, Any]:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    url = f"{COMMONS_API}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                _last_request_at = time.monotonic()
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise
            time.sleep(min(5 * (attempt + 1), 20))
    raise RuntimeError("Wikimedia Commons API remained unavailable after retries")


def request_bytes(url: str) -> bytes:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    for attempt in range(5):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                _last_request_at = time.monotonic()
                data = response.read(MAX_IMAGE_BYTES + 1)
                if len(data) > MAX_IMAGE_BYTES:
                    raise RuntimeError("Commons thumbnail exceeds 2 MiB")
                return data
        except urllib.error.HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise
            time.sleep(min(5 * (attempt + 1), 20))
    raise RuntimeError("Wikimedia thumbnail remained unavailable after retries")


def commons_candidates(query: str) -> list[dict[str, Any]]:
    data = request_json(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": "6",
            "gsrlimit": "10",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": "640",
            "format": "json",
            "formatversion": "2",
            "origin": "*",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    return sorted(pages, key=lambda page: page.get("index", 10_000))


def license_url(metadata: dict[str, Any], short_name: str) -> str:
    value = metadata.get("LicenseUrl", {}).get("value")
    if value:
        return f"https:{value}" if value.startswith("//") else value
    if short_name in {"CC0", "Public domain"}:
        return PUBLIC_DOMAIN_LICENSE_URL
    return ""


def suffix_for(media_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[media_type]


def entry_for(
    spec: dict[str, Any],
    page: dict[str, Any],
    info: dict[str, Any],
    data: bytes,
    media_type: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    metadata = info["extmetadata"]
    short_license = metadata["LicenseShortName"]["value"]
    relative_path = f"assets/{spec['cohort']}/{spec['id']}{suffix_for(media_type)}"
    page_title = page["title"]
    source_page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
        page_title.replace(" ", "_"), safe=":()/"
    )
    return {
        "dataset_version": DATASET_VERSION,
        "id": spec["id"],
        "cohort": spec["cohort"],
        "holdout_role": "recognition_candidate",
        "prompt_tuning_allowed": False,
        "candidate_query": spec["query"],
        "selection_rank": spec["selection_rank"],
        "source": {
            "dataset": "Wikimedia Commons",
            "source_id": str(page["pageid"]),
            "file_title": page_title,
            "source_page": source_page,
            "image_url": info["thumburl"],
            "original_image_url": info["url"],
            "license": short_license,
            "license_url": license_url(metadata, short_license),
            "artist": plain_text(metadata.get("Artist", {}).get("value")),
            "credit": plain_text(metadata.get("Credit", {}).get("value")),
            "attribution_required": short_license not in {"CC0", "Public domain"},
        },
        "local_path": relative_path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "media_type": media_type,
        "width": width,
        "height": height,
        "gold": {
            "is_food": spec["cohort"] != "nonfood",
            "names": spec["names"],
            "should_abstain": spec["cohort"] == "nonfood",
            "top3_metric_eligible": spec["cohort"] != "nonfood",
            "model_must_not_output_mass": True,
            "model_must_not_output_calorie_point_estimate": True,
        },
        "privacy_review": {
            "status": "pending",
            "contains_face": None,
            "contains_minor": None,
            "contains_document_or_health_data": None,
            "contains_location_or_personal_identifier": None,
        },
        "visual_qa": {
            "status": "pending",
            "food_matches_gold": None,
            "answer_overlay_leakage": None,
            "usable_resolution": width >= MIN_DIMENSION and height >= MIN_DIMENSION,
        },
        "sealed": False,
        "sealed_on": None,
    }


def choose_entry(
    spec: dict[str, Any],
    *,
    blocked_page_ids: set[str],
    blocked_hashes: set[str],
) -> tuple[dict[str, Any], dict[str, Any], bytes, str, int, int]:
    candidates = commons_candidates(spec["query"])
    valid: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for page in candidates:
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        short_license = metadata.get("LicenseShortName", {}).get("value")
        if (
            short_license not in ALLOWED_LICENSES
            or info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}
            or not info.get("thumburl")
            or not info.get("url")
            or str(page.get("pageid")) in blocked_page_ids
        ):
            continue
        valid.append((page, info))
    rank = spec["selection_rank"]
    if rank >= len(valid):
        raise RuntimeError(
            f"{spec['id']} has only {len(valid)} licensed candidates, rank {rank} requested"
        )
    for page, info in valid[rank:]:
        data = request_bytes(info["thumburl"])
        media_type, width, height = image_utils.image_metadata(data)
        digest = hashlib.sha256(data).hexdigest()
        if width < MIN_DIMENSION or height < MIN_DIMENSION or digest in blocked_hashes:
            continue
        return page, info, data, media_type, width, height
    raise RuntimeError(f"{spec['id']} has no unique candidate at usable resolution")


def curate() -> None:
    if MANIFEST.exists():
        raise RuntimeError("sealed manifest already exists; refusing to recurate")
    entries = read_jsonl(CANDIDATE_MANIFEST) if CANDIDATE_MANIFEST.exists() else []
    existing_by_id = {entry["id"]: entry for entry in entries}
    used_page_ids = {entry["source"]["source_id"] for entry in entries}
    used_hashes = {entry["sha256"] for entry in entries}
    for position, spec in enumerate(SPECS, start=1):
        if spec["id"] in existing_by_id:
            print(
                f"[{position:02d}/{len(SPECS)}] {spec['id']} <- resume existing candidate",
                flush=True,
            )
            continue
        page, info, data, media_type, width, height = choose_entry(
            spec,
            blocked_page_ids=used_page_ids,
            blocked_hashes=used_hashes,
        )
        entry = entry_for(spec, page, info, data, media_type, width, height)
        path = ROOT / entry["local_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entries.append(entry)
        used_page_ids.add(entry["source"]["source_id"])
        used_hashes.add(entry["sha256"])
        write_jsonl(CANDIDATE_MANIFEST, entries)
        print(
            f"[{position:02d}/{len(SPECS)}] {spec['id']} <- {page['title']} "
            f"({entry['source']['license']}, {len(data)} bytes)",
            flush=True,
        )
    verify_entries(entries, sealed=False)


def replace(sample_id: str) -> None:
    if MANIFEST.exists():
        raise RuntimeError("sealed manifest already exists; refusing replacement")
    entries = read_jsonl(CANDIDATE_MANIFEST)
    matching_specs = [spec for spec in SPECS if spec["id"] == sample_id]
    if len(matching_specs) != 1:
        raise RuntimeError(f"unknown sample ID: {sample_id}")
    indexes = [index for index, entry in enumerate(entries) if entry["id"] == sample_id]
    if len(indexes) != 1:
        raise RuntimeError(
            f"candidate manifest does not contain exactly one {sample_id}"
        )
    blocked_page_ids = {entry["source"]["source_id"] for entry in entries}
    blocked_hashes = {entry["sha256"] for entry in entries}
    page, info, data, media_type, width, height = choose_entry(
        matching_specs[0],
        blocked_page_ids=blocked_page_ids,
        blocked_hashes=blocked_hashes,
    )
    replacement = entry_for(
        matching_specs[0],
        page,
        info,
        data,
        media_type,
        width,
        height,
    )
    path = ROOT / replacement["local_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    entries[indexes[0]] = replacement
    write_jsonl(CANDIDATE_MANIFEST, entries)
    print(
        f"replaced {sample_id} <- {page['title']} "
        f"({replacement['source']['license']}, {len(data)} bytes)",
        flush=True,
    )
    verify_entries(entries, sealed=False)


def replace_flagged() -> None:
    for sample_id in INITIAL_QA_REPLACEMENTS:
        replace(sample_id)


def replace_second_flagged() -> None:
    for sample_id in SECOND_QA_REPLACEMENTS:
        replace(sample_id)


def replace_third_flagged() -> None:
    for sample_id in THIRD_QA_REPLACEMENTS:
        replace(sample_id)


def previous_data() -> tuple[set[str], set[str], set[str]]:
    datasets: set[str] = set()
    source_ids: set[str] = set()
    hashes: set[str] = set()
    for path in (
        ROOT.parent / "food_image_real" / "manifest.jsonl",
        ROOT.parent / "food_image_holdout" / "manifest.jsonl",
    ):
        for entry in read_jsonl(path):
            datasets.add(entry["source"]["dataset"])
            source_ids.add(entry["source"]["source_id"])
            hashes.add(entry["sha256"])
    scale_path = ROOT.parent / "food_image_scale_holdout" / "manifest.jsonl"
    for entry in read_jsonl(scale_path):
        for variant in ("with_ruler", "without_ruler"):
            hashes.add(entry[variant]["sha256"])
    return datasets, source_ids, hashes


def verify_entries(entries: list[dict[str, Any]], *, sealed: bool) -> None:
    if len(entries) != sum(EXPECTED_COUNTS.values()):
        raise RuntimeError(f"expected 60 samples, found {len(entries)}")
    counts: dict[str, int] = {}
    ids: set[str] = set()
    source_ids: set[str] = set()
    hashes: set[str] = set()
    total_bytes = 0
    previous_datasets, previous_source_ids, previous_hashes = previous_data()
    for entry in entries:
        counts[entry["cohort"]] = counts.get(entry["cohort"], 0) + 1
        if entry["id"] in ids:
            raise RuntimeError(f"duplicate sample ID: {entry['id']}")
        ids.add(entry["id"])
        source_id = entry["source"]["source_id"]
        if source_id in source_ids or source_id in previous_source_ids:
            raise RuntimeError(f"duplicate or previously used source ID: {entry['id']}")
        source_ids.add(source_id)
        if entry["source"]["dataset"] in previous_datasets:
            raise RuntimeError(f"previous source dataset reused: {entry['id']}")
        if entry["source"]["dataset"] != "Wikimedia Commons":
            raise RuntimeError(f"unexpected source dataset: {entry['id']}")
        if entry["source"]["license"] not in ALLOWED_LICENSES:
            raise RuntimeError(f"unapproved license: {entry['id']}")
        if not entry["source"]["license_url"] or not entry["source"]["source_page"]:
            raise RuntimeError(f"incomplete license provenance: {entry['id']}")
        digest = entry["sha256"]
        if digest in hashes or digest in previous_hashes:
            raise RuntimeError(f"duplicate or previously used bytes: {entry['id']}")
        hashes.add(digest)
        path = ROOT / entry["local_path"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError(f"asset hash mismatch: {entry['id']}")
        media_type, width, height = image_utils.image_metadata(data)
        if (media_type, width, height, len(data)) != (
            entry["media_type"],
            entry["width"],
            entry["height"],
            entry["byte_length"],
        ):
            raise RuntimeError(f"asset metadata mismatch: {entry['id']}")
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            raise RuntimeError(f"asset resolution too small: {entry['id']}")
        total_bytes += len(data)
        gold = entry["gold"]
        if (
            gold.get("model_must_not_output_mass") is not True
            or gold.get("model_must_not_output_calorie_point_estimate") is not True
            or "total_mass_g" in gold
            or "total_calories_kcal" in gold
        ):
            raise RuntimeError(
                f"recognition-only gold contract violated: {entry['id']}"
            )
        if sealed:
            if (
                not entry.get("sealed")
                or entry.get("sealed_on") != SEALED_ON
                or entry.get("holdout_role") != "sealed_recognition_only"
                or entry["privacy_review"].get("status") != "passed"
                or entry["visual_qa"].get("status") != "passed"
            ):
                raise RuntimeError(f"sealed QA contract violated: {entry['id']}")
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"cohort counts mismatch: {counts}")
    if total_bytes > MAX_DATASET_BYTES:
        raise RuntimeError(f"dataset exceeds 60 MiB: {total_bytes}")
    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "samples": len(entries),
                "cohorts": counts,
                "assets_bytes": total_bytes,
                "source_dataset": "Wikimedia Commons",
                "previous_dataset_overlap": 0,
                "previous_source_id_overlap": 0,
                "previous_sha256_overlap": 0,
                "provider_calls": 0,
                "sealed": sealed,
                "status": "verified_sealed"
                if sealed
                else "verified_candidates_qa_pending",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def attest_qa() -> None:
    if MANIFEST.exists():
        raise RuntimeError("sealed manifest already exists")
    entries = read_jsonl(CANDIDATE_MANIFEST)
    for entry in entries:
        entry["privacy_review"] = {
            "status": "passed",
            "contains_face": False,
            "contains_minor": False,
            "contains_document_or_health_data": False,
            "contains_location_or_personal_identifier": False,
            "reviewed_on": SEALED_ON,
            "review_method": "full_contact_sheet_and_targeted_original_thumbnail_review",
        }
        entry["visual_qa"] = {
            "status": "passed",
            "food_matches_gold": True,
            "answer_overlay_leakage": False,
            "usable_resolution": True,
            "reviewed_on": SEALED_ON,
            "review_method": "full_contact_sheet_and_targeted_original_thumbnail_review",
        }
    write_jsonl(CANDIDATE_MANIFEST, entries)
    verify_entries(entries, sealed=False)


def seal() -> None:
    if MANIFEST.exists():
        raise RuntimeError("sealed manifest already exists")
    entries = read_jsonl(CANDIDATE_MANIFEST)
    for entry in entries:
        if (
            entry["privacy_review"].get("status") != "passed"
            or entry["visual_qa"].get("status") != "passed"
        ):
            raise RuntimeError(f"QA is not passed: {entry['id']}")
        entry["holdout_role"] = "sealed_recognition_only"
        entry["sealed"] = True
        entry["sealed_on"] = SEALED_ON
    write_jsonl(MANIFEST, entries)
    verify_entries(entries, sealed=True)


def verify() -> None:
    path = MANIFEST if MANIFEST.exists() else CANDIDATE_MANIFEST
    if not path.exists():
        raise RuntimeError("no candidate or sealed manifest exists")
    verify_entries(read_jsonl(path), sealed=path == MANIFEST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "curate",
            "verify",
            "replace",
            "replace-flagged",
            "replace-second-flagged",
            "replace-third-flagged",
            "attest-qa",
            "seal",
        ),
    )
    parser.add_argument("--sample-id")
    args = parser.parse_args()
    try:
        if args.command == "replace":
            if not args.sample_id:
                raise RuntimeError("--sample-id is required for replace")
            replace(args.sample_id)
        elif args.command == "replace-flagged":
            replace_flagged()
        elif args.command == "replace-second-flagged":
            replace_second_flagged()
        elif args.command == "replace-third-flagged":
            replace_third_flagged()
        else:
            {
                "curate": curate,
                "verify": verify,
                "attest-qa": attest_qa,
                "seal": seal,
            }[args.command]()
    except (
        KeyError,
        OSError,
        RuntimeError,
        ValueError,
        urllib.error.URLError,
    ) as error:
        print(f"food-image recognition holdout error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
