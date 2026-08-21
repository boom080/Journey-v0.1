#!/usr/bin/env python3
"""Journey Demo preflight. It reports conflicts and never stops other projects."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "QWEN_API_KEY",
    "glm": "GLM_API_KEY",
    "kimi": "KIMI_API_KEY",
    "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
}


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def docker_bindings() -> list[dict[str, str]]:
    result = run("docker", "ps", "--format", "{{json .}}", check=False)
    if result.returncode:
        return []
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def listener_detail(port: int, containers: list[dict[str, str]]) -> str | None:
    for item in containers:
        if f"127.0.0.1:{port}->" in item.get("Ports", "") or f"0.0.0.0:{port}->" in item.get(
            "Ports", ""
        ):
            return f"Docker container {item.get('Names')} (project={item.get('Labels', 'unknown')})"
    with socket.socket() as probe:
        probe.settimeout(0.2)
        if probe.connect_ex(("127.0.0.1", port)) != 0:
            return None
    detail = run("lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", check=False)
    first = next((line for line in detail.stdout.splitlines()[1:] if line.strip()), "unknown process")
    return first


def compose_json() -> list[dict]:
    result = run("docker", "compose", "ps", "--format", "json", check=False)
    if result.returncode:
        return []
    payload = result.stdout.strip()
    if not payload:
        return []
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [json.loads(line) for line in payload.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-start", action="store_true")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    print(f"workspace={ROOT}")
    docker = run("docker", "info", check=False)
    if docker.returncode:
        errors.append("Docker is not ready. Start Docker Desktop first.")
    else:
        print("docker=READY")

    env = {**load_env(args.env_file), **os.environ}
    if not args.env_file.exists():
        errors.append(f"Environment file is missing: {args.env_file}")
    else:
        print(f"env_file={args.env_file.name}")

    provider = env.get("AGENT_PROVIDER", "mock").strip().lower()
    mode = "MOCK" if provider == "mock" else "REAL"
    print(f"agent_mode={mode} provider={provider}")
    if provider != "mock":
        key_name = PROVIDER_KEYS.get(provider, "AGENT_API_KEY")
        legacy_key_allowed = provider in {"openai", "deepseek", "openai_compatible"}
        if not env.get(key_name) and not (legacy_key_allowed and env.get("AGENT_API_KEY")):
            suffix = " or AGENT_API_KEY" if legacy_key_allowed else ""
            errors.append(f"REAL provider requires non-empty {key_name}{suffix}")
        try:
            if float(env.get("AGENT_DAILY_BUDGET_USD", "0")) <= 0:
                errors.append("REAL provider requires AGENT_DAILY_BUDGET_USD > 0")
        except ValueError:
            errors.append("AGENT_DAILY_BUDGET_USD must be numeric")

    api_port = int(env.get("API_PORT", "8000"))
    postgres_port = int(env.get("POSTGRES_PORT", "55432"))
    containers = docker_bindings()
    for name, port in (("API_PORT", api_port), ("POSTGRES_PORT", postgres_port)):
        detail = listener_detail(port, containers)
        if detail and "journey-" not in detail:
            errors.append(f"Port {port} ({name}) is already occupied by {detail}")
        elif detail:
            warnings.append(f"Port {port} ({name}) is already owned by the running Journey stack")
        else:
            print(f"port_{port}=AVAILABLE")

    config = run("docker", "compose", "config", "--quiet", check=False)
    if config.returncode:
        errors.append(f"Compose config is invalid: {config.stderr.strip()}")
    else:
        print("compose_config=VALID")

    projects = run("docker", "compose", "ls", "--format", "json", check=False)
    if projects.returncode == 0:
        names = [item.get("Name") for item in json.loads(projects.stdout or "[]")]
        print(f"compose_projects={','.join(filter(None, names)) or 'none'}")

    if args.after_start and not errors:
        services = compose_json()
        unhealthy = [
            item
            for item in services
            if item.get("Service") in {"api", "db"}
            and item.get("Health") not in {"healthy", ""}
        ]
        if unhealthy:
            errors.append(f"Core services are not healthy: {unhealthy}")
        else:
            print("compose_core=HEALTHY")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{api_port}/health/ready", timeout=5
            ) as response:
                ready = json.loads(response.read())
            print(
                "backend_ready="
                f"{ready.get('status')} database={ready.get('database')} rag={ready.get('rag')} "
                f"agent={ready.get('agent_mode')}/{ready.get('agent_provider')}"
            )
            if ready.get("status") != "ok" or ready.get("rag") != "ok":
                errors.append(f"Backend readiness gate failed: {ready}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            errors.append(f"Backend readiness request failed: {error}")
        current = run("docker", "compose", "exec", "-T", "api", "alembic", "current", check=False)
        heads = run("docker", "compose", "exec", "-T", "api", "alembic", "heads", check=False)
        if current.returncode or heads.returncode or not any(
            line.split()[0] in current.stdout for line in heads.stdout.splitlines() if line.strip()
        ):
            errors.append("Alembic migration is not at head")
        else:
            print(f"migration={current.stdout.strip()}")

    for warning in warnings:
        print(f"WARN {warning}")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    print(f"preflight={'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
