"""Read-only release check. Never prints secrets or approves a provider."""

import json

from app.core.provider_review import review_is_current
from app.core.settings import get_settings
from app.services.agent_privacy import disclosure_version


def main() -> int:
    settings = get_settings()
    disclosure_sha256 = disclosure_version(settings)
    review_ready = settings.agent_provider != "mock" and review_is_current(
        settings.agent_provider_review_json, disclosure_sha256
    )
    local_personal_mode = (
        settings.environment == "local" and not settings.agent_provider_review_required
    )
    print(
        json.dumps(
            {
                "provider": settings.agent_provider,
                "disclosure_sha256": disclosure_sha256,
                "review_ready": review_ready,
                "local_personal_mode": local_personal_mode,
                "external_enabled": settings.agent_external_enabled,
                "privacy_release_gate_ready": review_ready and settings.agent_external_enabled,
            }
        )
    )
    return 0 if review_ready and settings.agent_external_enabled else 1


if __name__ == "__main__":
    raise SystemExit(main())
