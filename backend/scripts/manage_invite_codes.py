import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.crud.invite_code import (  # noqa: E402
    create_invite_code,
    get_invite_code_by_code,
    get_invite_code_effective_status,
    list_invite_codes,
    update_invite_code_status,
)
from app.models.user import User  # noqa: F401, E402


def parse_datetime(value: Optional[str]):
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    normalized = normalized.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def serialize_invite_code(invite_code):
    return {
        "id": invite_code.id,
        "code": invite_code.code,
        "stored_status": invite_code.status,
        "effective_status": get_invite_code_effective_status(invite_code),
        "max_uses": invite_code.max_uses,
        "used_count": invite_code.used_count,
        "used_by_user_id": invite_code.used_by_user_id,
        "used_by_openid": invite_code.used_by_openid,
        "expires_at": invite_code.expires_at.isoformat() if invite_code.expires_at else None,
        "created_at": invite_code.created_at.isoformat() if invite_code.created_at else None,
        "updated_at": invite_code.updated_at.isoformat() if invite_code.updated_at else None,
    }


def handle_list(_args):
    with SessionLocal() as db:
        payload = [serialize_invite_code(item) for item in list_invite_codes(db)]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def handle_create(args):
    created = []

    with SessionLocal() as db:
        expires_at = parse_datetime(args.expires_at)
        for code in args.codes:
            created.append(
                serialize_invite_code(
                    create_invite_code(
                        db,
                        code,
                        max_uses=1,
                        expires_at=expires_at,
                        status=args.status,
                    )
                )
            )

    print(json.dumps(created, ensure_ascii=False, indent=2))


def handle_disable(args):
    updated = []

    with SessionLocal() as db:
        for code in args.codes:
            invite_code = get_invite_code_by_code(db, code)
            if not invite_code:
                raise ValueError(f"Invite code not found: {code}")
            updated.append(serialize_invite_code(update_invite_code_status(db, invite_code, "disabled")))

    print(json.dumps(updated, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Manage invite codes for the Journey backend database."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List all invite codes")
    list_parser.set_defaults(handler=handle_list)

    create_parser = subparsers.add_parser("create", help="Create one or more single-use invite codes")
    create_parser.add_argument("codes", nargs="+", help="Invite code value(s) to create")
    create_parser.add_argument(
        "--status",
        choices=["unused", "disabled"],
        default="unused",
        help="Initial stored status for the new invite code",
    )
    create_parser.add_argument(
        "--expires-at",
        default="",
        help="Optional UTC expire time in ISO 8601, for example 2026-05-01T00:00:00 or 2026-05-01T00:00:00Z",
    )
    create_parser.set_defaults(handler=handle_create)

    disable_parser = subparsers.add_parser("disable", help="Disable one or more existing invite codes")
    disable_parser.add_argument("codes", nargs="+", help="Invite code value(s) to disable")
    disable_parser.set_defaults(handler=handle_disable)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.handler(args)
    except Exception as exc:  # pragma: no cover - operator-facing script
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
