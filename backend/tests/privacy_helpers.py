"""Synthetic deployment review for fake adapters; not a deployable approval."""

import json
from datetime import UTC, datetime, timedelta

from app.services.agent_privacy import disclosure_version


def synthetic_review(settings):
    now = datetime.now(UTC)
    return json.dumps(
        {
            "status": "approved",
            "scope": "journey-text-agent",
            "disclosure_sha256": disclosure_version(settings),
            "reviewed_by": "synthetic-test-fixture",
            "reviewed_at": now.isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "retention_evidence": "test-only:no-network-retention",
            "deletion_evidence": "test-only:no-network-deletion",
            "restore_evidence": "test-only:isolated-restore",
        }
    )
