# Journey resume evaluation v1

Only synthetic data is sent to the configured model. No product logic is changed.

## Reproduction

Run from repository root. Python dependencies: `UV_CACHE_DIR=/private/tmp/journey-uv-cache uv sync --project backend --extra dev --frozen --no-install-project` (plain editable installation currently fails package discovery). PostgreSQL 18.6 and Node version are recorded in raw/manifest.json.

Create an isolated PostgreSQL cluster in `/private/tmp/journey-resume-pg`, listening only on `127.0.0.1:55439`, with databases `journey_test` (destructive pytest fixtures) and `journey_resume_eval` (synthetic model evaluation). NEVER redirect runtime.py to a business database. The local role in this run is p668. Run existing Alembic migrations to head for both databases. To reproduce exact RAG prompts, restore `evaluation/raw/knowledge_snapshot.sql` into the empty migrated `journey_resume_eval` database before running RAG; the UUIDs in the snapshot are included in model prompts.

Archive `evaluation/raw` before another full run. Scripts refuse to overwrite model outputs; they must not append different datasets/environments to one run. Keep the dataset files and source hashes from manifest.json. Configured model credentials are read from `.env` without storing them; reproduce nonsecret settings from the manifest. External provider output is not guaranteed bitwise deterministic despite temperature 0. DB timezone for this run is Asia/Shanghai, as explicitly captured by the audit.

```sh
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/run_backend.py
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest scripts/evaluation/test_reliability.py -q --junitxml=evaluation/raw/reliability-all.xml
npm run test:components --workspace @journey/mobile -- --json --outputFile="$PWD/evaluation/raw/mobile.json"
npm run test:logic --workspace @journey/mobile
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/parsing.py --execute
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/rag.py
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/summary_performance.py
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/manifest.py
PYTHONPATH=backend:. backend/.venv/bin/python scripts/evaluation/report.py
```

Run DB-clearing backend tests before reliability tests. Do not rerun reliability against previously populated synthetic users without resetting the isolated test database. The first recorded run used reliability.xml (6 cases) plus run-reexecution.xml (1 case); a new full run uses reliability-all.xml. The lost_response case is a sequential application-level lost-response simulation, not a TCP failure or crash/restart injection. same_run_request_reexecuted explicitly tests a duplicated parsing request followed by confirming each returned candidate.

Gold answers have not been approved by a human. Dataset-based rates are provisional scoring measurements, not human-validated accuracy. Explicit kcal literals are extraction labels, never nutritional truth. True semantic correctness/grounding/hallucination rates require per-answer human labels. Actual billing and CNY cost require validated tariff/billing evidence and an agreed exchange rate; configured USD estimates remain separate.
