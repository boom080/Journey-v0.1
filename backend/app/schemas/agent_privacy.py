from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class AgentPrivacyStatus(BaseModel):
    provider: str
    external: bool
    enabled: bool
    policy_version: str
    consent_granted: bool
    granted_at: datetime | None
    retention_days: int
    notice: str
    data_sent: list[str]
    provider_policy_url: str | None
    provider_retention_notice: str
    deletion_notice: str


class AgentConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted: StrictBool
    policy_version: str = Field(min_length=1, max_length=64)


class AgentDataDeletion(BaseModel):
    deleted_runs: int
    deleted_threads: int
    consent_revoked: Literal[True] = True
    provider_data_deleted: Literal[False] = False
    message: str
