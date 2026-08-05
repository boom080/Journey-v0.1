import json
from pathlib import Path

from app.main import app


def export_openapi() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    content = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    targets = (
        repository_root / "backend/tests/snapshots/openapi.json",
        repository_root / "packages/contracts/openapi.json",
    )
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    export_openapi()
