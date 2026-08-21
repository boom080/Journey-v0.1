#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_dir"

python3 infra/demo/preflight.py
docker compose up -d --build --wait
python3 infra/demo/preflight.py --after-start
