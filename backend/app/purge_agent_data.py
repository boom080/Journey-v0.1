"""Optional operator command: python -m app.purge_agent_data (after migrations)."""

from app.services.agent_privacy import purge_expired_agent_data

if __name__ == "__main__":
    purge_expired_agent_data()
