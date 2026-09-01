"""Read-only release check. Never prints secrets or approves a provider."""

import json

from app.core.settings import get_settings
from app.services.agent_privacy import disclosure_version, provider_review_ready


def main() -> int:
    settings = get_settings()
    ready = settings.agent_provider != "mock" and provider_review_ready(settings)
    print(
        json.dumps(
            {
                "provider": settings.agent_provider,
                "disclosure_sha256": disclosure_version(settings),
                "review_ready": ready,
                "external_enabled": settings.agent_external_enabled,
                "privacy_release_gate_ready": ready and settings.agent_external_enabled,
            }
        )
    )
    return 0 if ready and settings.agent_external_enabled else 1


if __name__ == "__main__":
    raise SystemExit(main())
