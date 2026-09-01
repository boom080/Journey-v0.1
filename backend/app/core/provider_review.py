"""Deployment-owner attestations, not an automatic legal/compliance approval.

Public provider policies alone cannot prove a deployment's retention/deletion
arrangements. Keep egress closed until an accountable owner supplies a current
review tied to this exact disclosure. No provider network requests are made.
"""

import json
from datetime import UTC, datetime, timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError


class ProviderReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    scope: str
    disclosure_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_by: str = Field(min_length=3, max_length=160)
    reviewed_at: AwareDatetime
    expires_at: AwareDatetime
    retention_evidence: str = Field(min_length=8, max_length=500)
    deletion_evidence: str = Field(min_length=8, max_length=500)
    restore_evidence: str = Field(min_length=8, max_length=500)


def review_is_current(raw: str, disclosure_sha256: str) -> bool:
    if not raw or len(raw) > 8000:
        return False
    try:
        review = ProviderReview.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError):
        return False
    now = datetime.now(UTC)
    return (
        review.status == "approved"
        and review.scope == "journey-text-agent"
        and review.disclosure_sha256 == disclosure_sha256
        and review.reviewed_at <= now < review.expires_at
        and review.expires_at - review.reviewed_at <= timedelta(days=90)
    )
