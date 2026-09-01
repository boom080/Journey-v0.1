import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.provider_review import review_is_current


def valid_review():
    now = datetime.now(UTC)
    return {
        "status": "approved",
        "scope": "journey-text-agent",
        "disclosure_sha256": "a" * 64,
        "reviewed_by": "synthetic-test-owner",
        "reviewed_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "retention_evidence": "synthetic:retention-proof",
        "deletion_evidence": "synthetic:deletion-proof",
        "restore_evidence": "synthetic:restore-proof",
    }


def test_review_requires_matching_disclosure_and_owner_attestation():
    review = json.dumps(valid_review())
    assert review_is_current(review, "a" * 64)
    assert not review_is_current(review, "b" * 64)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "pending"),
        ("scope", "images"),
        ("deletion_evidence", ""),
        ("retention_evidence", ""),
        ("restore_evidence", ""),
        ("reviewed_by", ""),
        ("reviewed_at", "2026-08-31T00:00:00"),
        ("expires_at", "2020-01-01T00:00:00Z"),
        ("expires_at", "2099-01-01T00:00:00Z"),
        ("reviewed_at", "2099-01-01T00:00:00Z"),
    ],
)
def test_incomplete_expired_or_unbounded_reviews_fail_closed(field, value):
    review = {**valid_review(), field: value}
    assert not review_is_current(json.dumps(review), "a" * 64)
