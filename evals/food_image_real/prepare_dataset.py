"""Curate, download, and verify the licensed Stage 9 food-image dataset.

The committed manifest is the reproducibility boundary. ``curate`` contacts the
official sources and intentionally rewrites it; ``download`` never reselects
samples and verifies every pinned SHA-256.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.jsonl"
ASSETS = ROOT / "assets"
DATASET_VERSION = "journey-food-image-real-v1"
USER_AGENT = "Journey/0.1 (Stage 9 licensed local evaluation)"

N5K_BUCKET = "https://storage.googleapis.com/nutrition5k_dataset/nutrition5k_dataset"
N5K_GCS_API = "https://storage.googleapis.com/storage/v1/b/nutrition5k_dataset/o"
N5K_SOURCE_PAGE = "https://github.com/google-research-datasets/Nutrition5k"
N5K_LICENSE = "https://creativecommons.org/licenses/by/4.0/"

OFF_API = "https://world.openfoodfacts.org/api/v2/product"
OFF_SOURCE_PAGE = "https://world.openfoodfacts.org/product"
OFF_LICENSE = "https://creativecommons.org/licenses/by-sa/3.0/"
OPENVERSE_API = "https://api.openverse.org/v1/images/"

CONDIMENTS = {
    "balsamic vinegar",
    "garlic",
    "lemon juice",
    "lime juice",
    "olive oil",
    "pepper",
    "salt",
    "soy sauce",
    "sugar",
    "vinegar",
}

ALIASES_ZH = {
    "apple": ["苹果"],
    "arugula": ["芝麻菜"],
    "bacon": ["培根"],
    "banana": ["香蕉"],
    "berries": ["莓果", "浆果"],
    "bok choy": ["小白菜", "青菜"],
    "bread": ["面包", "吐司"],
    "broccoli": ["西兰花", "绿花椰菜"],
    "brown rice": ["糙米", "糙米饭"],
    "carrot": ["胡萝卜"],
    "cauliflower": ["花椰菜", "菜花"],
    "cheese pizza": ["芝士披萨", "奶酪披萨", "披萨"],
    "cherry tomatoes": ["圣女果", "小番茄"],
    "chicken": ["鸡肉"],
    "chicken apple sausage": ["鸡肉苹果香肠", "鸡肉香肠", "香肠"],
    "cucumbers": ["黄瓜"],
    "dumplings": ["饺子"],
    "fish": ["鱼", "鱼肉"],
    "fried rice": ["炒饭"],
    "grapes": ["葡萄"],
    "kale": ["羽衣甘蓝"],
    "lasagna": ["千层面", "意大利千层面"],
    "mixed greens": ["混合生菜", "沙拉菜", "蔬菜沙拉", "沙拉"],
    "mushroom": ["蘑菇"],
    "noodles": ["面条"],
    "oatmeal": ["燕麦粥", "燕麦"],
    "onions": ["洋葱"],
    "pineapple": ["菠萝", "凤梨"],
    "potatoes": ["土豆", "马铃薯"],
    "rice noodles": ["米粉", "米线"],
    "roasted potatoes": ["烤土豆", "烤马铃薯"],
    "scrambled eggs": ["炒蛋", "炒鸡蛋", "鸡蛋"],
    "spinach (raw)": ["菠菜"],
    "steak": ["牛排"],
    "sweet potato": ["红薯", "地瓜"],
    "tofu": ["豆腐"],
    "tomatoes": ["番茄", "西红柿"],
    "white rice": ["白米饭", "米饭"],
}

PREFERRED_SINGLES = [
    "apple",
    "dumplings",
    "berries",
    "broccoli",
    "brown rice",
    "carrot",
    "cauliflower",
    "cheese pizza",
    "cherry tomatoes",
    "chicken",
    "cucumbers",
    "fish",
    "fried rice",
    "grapes",
    "lasagna",
    "mixed greens",
    "mushroom",
    "oatmeal",
    "onions",
    "pineapple",
    "potatoes",
    "steak",
    "roasted potatoes",
    "scrambled eggs",
    "spinach (raw)",
    "sweet potato",
    "tofu",
    "tomatoes",
    "white rice",
    "bok choy",
]

# Product records were inspected through the official API on 2026-07-28.
# Values are fetched again during curation and frozen into the manifest.
OFF_PRODUCTS = [
    ("beverage", "5449000000996", ["coca-cola", "coke", "可口可乐", "可乐", "汽水"]),
    ("beverage", "5449000011527", ["fanta orange", "fanta", "芬达", "橙味汽水"]),
    ("beverage", "9002490100070", ["red bull", "红牛", "能量饮料"]),
    ("beverage", "0049000028911", ["diet coke", "健怡可乐", "无糖可乐"]),
    ("beverage", "3068320120256", ["evian", "依云", "矿泉水", "水"]),
    ("beverage", "8002270014901", ["s. pellegrino", "圣培露", "气泡水", "水"]),
    ("beverage", "5449000131805", ["coca-cola zero", "零度可乐", "无糖可乐"]),
    ("beverage", "7394376616501", ["oat drink", "oat milk", "燕麦奶", "燕麦饮"]),
    ("beverage", "5411188110835", ["alpro almond drink", "almond milk", "杏仁奶"]),
    ("beverage", "6111035000430", ["sidi ali", "矿泉水", "水"]),
    ("packaged", "7622210449283", ["prince chocolate biscuits", "巧克力饼干", "饼干"]),
    ("packaged", "5000159461122", ["snickers", "士力架", "巧克力棒"]),
    ("packaged", "5053990156009", ["pringles original", "品客", "薯片"]),
    ("packaged", "0028400090896", ["doritos nacho cheese", "多力多滋", "玉米片"]),
    ("packaged", "8076800195057", ["barilla spaghetti", "意大利面", "意面"]),
    ("packaged", "5000157024671", ["heinz beanz", "亨氏焗豆", "茄汁焗豆"]),
    ("packaged", "3228857000852", ["sliced bread", "切片面包", "吐司"]),
    ("packaged", "8000500310427", ["nutella biscuits", "能多益饼干", "榛子可可饼干"]),
    ("packaged", "7614500010013", ["toblerone", "瑞士三角巧克力", "巧克力"]),
    (
        "packaged",
        "3046920022651",
        ["lindt 70% chocolate", "瑞士莲黑巧克力", "黑巧克力"],
    ),
]

OPENVERSE_QUERIES = [
    ("keyboard", "computer keyboard object"),
    ("chair", "wooden chair object"),
    ("shoe", "running shoe object"),
    ("bicycle", "bicycle object"),
    ("headphones", "headphones object"),
    ("notebook", '"blank notebook"'),
    ("houseplant", '"potted fern"'),
    ("traffic_light", '"traffic light" closeup'),
    ("dumbbell", '"fitness dumbbell"'),
    ("guitar", '"acoustic guitar" isolated'),
]


def request_bytes(url: str, *, attempts: int = 5) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(min(8, 2**attempt))
    raise RuntimeError("unreachable")


def request_json(url: str) -> dict[str, Any]:
    return json.loads(request_bytes(url).decode("utf-8"))


def parse_n5k_row(row: list[str]) -> dict[str, Any]:
    ingredients = []
    for index in range(6, len(row), 7):
        if index + 6 >= len(row):
            break
        ingredients.append(
            {
                "id": row[index],
                "name": row[index + 1].strip().lower(),
                "grams": float(row[index + 2]),
                "calories": float(row[index + 3]),
            }
        )
    return {
        "dish_id": row[0],
        "total_calories": float(row[1]),
        "total_mass": float(row[2]),
        "ingredients": ingredients,
    }


def load_n5k_metadata() -> list[dict[str, Any]]:
    records = []
    for cafe in ("cafe1", "cafe2"):
        url = f"{N5K_BUCKET}/metadata/dish_metadata_{cafe}.csv"
        text = request_bytes(url).decode("utf-8")
        records.extend(parse_n5k_row(row) for row in csv.reader(text.splitlines()))
    return records


def list_n5k_rgb() -> dict[str, dict[str, Any]]:
    prefix = "nutrition5k_dataset/imagery/realsense_overhead/"
    token = None
    result: dict[str, dict[str, Any]] = {}
    while True:
        params = {"prefix": prefix, "maxResults": "1000"}
        if token:
            params["pageToken"] = token
        payload = request_json(f"{N5K_GCS_API}?{urllib.parse.urlencode(params)}")
        for item in payload.get("items", []):
            name = item["name"]
            if not name.endswith("/rgb.png"):
                continue
            dish_id = name.split("/")[-2]
            result[dish_id] = {
                "url": f"https://storage.googleapis.com/nutrition5k_dataset/{name}",
                "size": int(item["size"]),
            }
        token = payload.get("nextPageToken")
        if not token:
            return result


def aliases(name: str) -> list[str]:
    return list(dict.fromkeys([name, *ALIASES_ZH.get(name, [])]))


def meaningful_ingredients(record: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        item
        for item in record["ingredients"]
        if item["name"] not in CONDIMENTS and item["grams"] >= 3
    ]
    return sorted(
        candidates or record["ingredients"],
        key=lambda item: item["grams"],
        reverse=True,
    )


def choose_n5k(
    records: list[dict[str, Any]], available: set[str]
) -> list[tuple[str, dict]]:
    usable = [
        record
        for record in records
        if record["dish_id"] in available
        and 15 <= record["total_mass"] <= 1500
        and 0 <= record["total_calories"] <= 3000
    ]
    selected: list[tuple[str, dict]] = []
    used: set[str] = set()

    for ingredient_name in PREFERRED_SINGLES:
        match = next(
            (
                record
                for record in usable
                if record["dish_id"] not in used
                and len(record["ingredients"]) == 1
                and record["ingredients"][0]["name"] == ingredient_name
            ),
            None,
        )
        if match:
            selected.append(("single_food", match))
            used.add(match["dish_id"])
    if len(selected) != 30:
        raise RuntimeError(f"expected 30 curated single foods, found {len(selected)}")

    mixed_pool = [
        record
        for record in usable
        if record["dish_id"] not in used
        and 3 <= len(record["ingredients"]) <= 8
        and len(meaningful_ingredients(record)) >= 2
    ]
    for record in mixed_pool[:: max(1, len(mixed_pool) // 30)][:30]:
        selected.append(("mixed_meal", record))
        used.add(record["dish_id"])
    if sum(category == "mixed_meal" for category, _ in selected) != 30:
        raise RuntimeError("could not select 30 mixed meals")

    difficult_pool = [
        record
        for record in usable
        if record["dish_id"] not in used and len(record["ingredients"]) >= 9
    ]
    for record in difficult_pool[:: max(1, len(difficult_pool) // 10)][:10]:
        selected.append(("difficult_meal", record))
        used.add(record["dish_id"])
    if sum(category == "difficult_meal" for category, _ in selected) != 10:
        raise RuntimeError("could not select 10 difficult meals")
    return selected


def image_metadata(data: bytes) -> tuple[str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", width, height
    if data.startswith(b"\xff\xd8\xff"):
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            length = struct.unpack(">H", data[offset : offset + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB}:
                height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
                return "image/jpeg", width, height
            offset += length
    raise ValueError("only PNG and JPEG evaluation assets are supported")


def save_asset(
    relative: str,
    url: str,
    *,
    refresh: bool = False,
    download_attempts: int = 5,
) -> dict[str, Any]:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        path.read_bytes()
        if path.exists() and not refresh
        else request_bytes(url, attempts=download_attempts)
    )
    media_type, width, height = image_metadata(data)
    path.write_bytes(data)
    return {
        "local_path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "media_type": media_type,
        "width": width,
        "height": height,
    }


def n5k_entries() -> list[dict[str, Any]]:
    rgb = list_n5k_rgb()
    records = load_n5k_metadata()
    selection = choose_n5k(records, set(rgb))
    entries = []
    counters = {"single_food": 0, "mixed_meal": 0, "difficult_meal": 0}
    for category, record in selection:
        counters[category] += 1
        sample_id = f"n5k-{category.replace('_', '-')}-{counters[category]:03d}"
        dish_id = record["dish_id"]
        ranked = meaningful_ingredients(record)
        gold_names = [
            {"canonical_en": item["name"], "aliases": aliases(item["name"])}
            for item in ranked[:3]
        ]
        relative = f"assets/nutrition5k/{dish_id}.png"
        asset = save_asset(relative, rgb[dish_id]["url"])
        entries.append(
            {
                "dataset_version": DATASET_VERSION,
                "id": sample_id,
                "category": category,
                "source": {
                    "dataset": "Nutrition5k",
                    "source_id": dish_id,
                    "source_page": N5K_SOURCE_PAGE,
                    "image_url": rgb[dish_id]["url"],
                    "license": "CC BY 4.0",
                    "license_url": N5K_LICENSE,
                    "attribution": "Thames et al., Nutrition5k, CVPR 2021",
                },
                **asset,
                "gold": {
                    "is_food": True,
                    "names": gold_names,
                    "total_mass_g": round(record["total_mass"], 3),
                    "total_calories_kcal": round(record["total_calories"], 3),
                    "should_abstain": False,
                    "top3_metric_eligible": True,
                    "portion_metric_eligible": category == "single_food",
                    "calorie_metric_eligible": True,
                    "difficulty_tags": (
                        ["many_ingredients", "no_explicit_scale"]
                        if category == "difficult_meal"
                        else ["no_explicit_scale"]
                    ),
                },
            }
        )
    return entries


def parse_quantity_grams(value: str, *, beverage: bool) -> float:
    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(fl\s*oz|oz|ml|cl|l|g|kg)\b",
        (value or "").lower(),
    )
    if not match:
        raise ValueError(f"unsupported package quantity: {value!r}")
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2)
    multiplier = {
        "fl oz": 29.5735,
        "oz": 28.3495,
        "ml": 1,
        "cl": 10,
        "l": 1000,
        "g": 1,
        "kg": 1000,
    }[unit.replace("  ", " ")]
    if beverage or unit in {"oz", "g", "kg"}:
        return amount * multiplier
    raise ValueError(f"cannot convert {value!r} to grams")


def off_entries() -> list[dict[str, Any]]:
    entries = []
    counters = {"beverage": 0, "packaged": 0}
    for category, code, expected_aliases in OFF_PRODUCTS:
        payload = request_json(
            f"{OFF_API}/{code}?fields=code,product_name,image_front_url,"
            "nutriments,serving_size,quantity"
        )
        product = payload.get("product") or {}
        name = (product.get("product_name") or "").strip()
        image_url = product.get("image_front_url")
        energy_100 = (product.get("nutriments") or {}).get("energy-kcal_100g")
        if not name or not image_url or energy_100 is None:
            raise RuntimeError(
                f"Open Food Facts product {code} lacks frozen evaluation fields"
            )
        beverage = category == "beverage"
        amount = parse_quantity_grams(product.get("quantity") or "", beverage=beverage)
        total_calories = amount * float(energy_100) / 100
        counters[category] += 1
        sample_id = f"off-{category}-{counters[category]:03d}"
        relative = f"assets/openfoodfacts/{code}.jpg"
        asset = save_asset(relative, image_url)
        entries.append(
            {
                "dataset_version": DATASET_VERSION,
                "id": sample_id,
                "category": category,
                "source": {
                    "dataset": "Open Food Facts",
                    "source_id": code,
                    "source_page": f"{OFF_SOURCE_PAGE}/{code}",
                    "image_url": image_url,
                    "license": "CC BY-SA 3.0",
                    "license_url": OFF_LICENSE,
                    "attribution": "Open Food Facts contributors",
                },
                **asset,
                "gold": {
                    "is_food": True,
                    "names": [
                        {
                            "canonical_en": name,
                            "aliases": list(dict.fromkeys([name, *expected_aliases])),
                        }
                    ],
                    "total_mass_g": round(amount, 3),
                    "total_calories_kcal": round(total_calories, 3),
                    "should_abstain": False,
                    "top3_metric_eligible": True,
                    "portion_metric_eligible": False,
                    "calorie_metric_eligible": True,
                    "difficulty_tags": ["packaging_text", "community_label"],
                },
            }
        )
        time.sleep(1)
    return entries


def openverse_entry(label: str, query: str, index: int) -> dict[str, Any]:
    params = {
        "q": f"{query} -food -people -person",
        "license": "by,by-sa,cc0,pdm",
        "extension": "jpg,jpeg,png",
        "mature": "false",
        "page_size": "20",
    }
    payload = request_json(f"{OPENVERSE_API}?{urllib.parse.urlencode(params)}")
    chosen = None
    asset = None
    relative = ""
    for result in payload.get("results", []):
        if (
            result.get("thumbnail")
            and result.get("foreign_landing_url")
            and result.get("license") in {"by", "by-sa", "cc0", "pdm"}
            and int(result.get("width") or 0) >= 400
            and int(result.get("height") or 0) >= 400
            and not result.get("mature")
        ):
            extension = (
                ".png" if str(result.get("filetype", "")).lower() == "png" else ".jpg"
            )
            relative = f"assets/openverse/{label}{extension}"
            try:
                asset = save_asset(
                    relative,
                    result["thumbnail"],
                    refresh=True,
                    download_attempts=1,
                )
            except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
                continue
            chosen = result
            break
    if not chosen or not asset:
        raise RuntimeError(f"no acceptable Openverse image for {query!r}")
    return {
        "dataset_version": DATASET_VERSION,
        "id": f"openverse-nonfood-{index:03d}",
        "category": "nonfood",
        "source": {
            "dataset": "Openverse",
            "source_id": chosen["id"],
            "title": chosen.get("title"),
            "source_page": chosen["foreign_landing_url"],
            "image_url": chosen["thumbnail"],
            "original_image_url": chosen.get("url"),
            "license": str(chosen["license"]).upper(),
            "license_url": chosen.get("license_url"),
            "attribution": chosen.get("attribution")
            or f"{chosen.get('title') or label} by {chosen.get('creator') or 'unknown'}",
            "provider": chosen.get("provider"),
            "indexed_source": chosen.get("source"),
        },
        **asset,
        "gold": {
            "is_food": False,
            "names": [],
            "total_mass_g": None,
            "total_calories_kcal": None,
            "should_abstain": True,
            "top3_metric_eligible": False,
            "portion_metric_eligible": False,
            "calorie_metric_eligible": False,
            "difficulty_tags": ["nonfood", label],
        },
    }


def curate() -> None:
    entries = n5k_entries()
    entries.extend(off_entries())
    for index, (label, query) in enumerate(OPENVERSE_QUERIES, start=1):
        entries.append(openverse_entry(label, query, index))
        time.sleep(1)
    if len(entries) != 100:
        raise RuntimeError(f"expected exactly 100 samples, got {len(entries)}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )
    verify()


def load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST.exists():
        raise RuntimeError("manifest.jsonl is missing; run the explicit curate command")
    return [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def download() -> None:
    for entry in load_manifest():
        path = ROOT / entry["local_path"]
        if (
            path.exists()
            and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        ):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(request_bytes(entry["source"]["image_url"]))
    verify()


def verify() -> None:
    entries = load_manifest()
    ids = {entry["id"] for entry in entries}
    categories: dict[str, int] = {}
    errors = []
    for entry in entries:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1
        path = ROOT / entry["local_path"]
        if not path.exists():
            errors.append(f"{entry['id']}: missing {entry['local_path']}")
            continue
        data = path.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != entry["sha256"]:
            errors.append(f"{entry['id']}: SHA-256 mismatch")
        try:
            media_type, width, height = image_metadata(data)
        except ValueError as error:
            errors.append(f"{entry['id']}: {error}")
            continue
        if (media_type, width, height, len(data)) != (
            entry["media_type"],
            entry["width"],
            entry["height"],
            entry["byte_length"],
        ):
            errors.append(f"{entry['id']}: image metadata drift")
    expected = {
        "single_food": 30,
        "mixed_meal": 30,
        "difficult_meal": 10,
        "beverage": 10,
        "packaged": 10,
        "nonfood": 10,
    }
    if len(entries) != 100 or len(ids) != 100 or categories != expected:
        errors.append(
            f"dataset structure mismatch: count={len(entries)} categories={categories}"
        )
    if errors:
        raise RuntimeError("\n".join(errors))
    print(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "samples": len(entries),
                "categories": categories,
                "assets_bytes": sum(entry["byte_length"] for entry in entries),
                "status": "verified",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("curate", "download", "verify"))
    args = parser.parse_args()
    {"curate": curate, "download": download, "verify": verify}[args.command]()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"food-image dataset error: {error}", file=sys.stderr)
        raise
