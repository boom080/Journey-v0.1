from sqlalchemy import text


USER_COLUMN_SQL = {
    "openid": "ALTER TABLE users ADD COLUMN openid VARCHAR(100)",
    "unionid": "ALTER TABLE users ADD COLUMN unionid VARCHAR(100)",
    "nickname": "ALTER TABLE users ADD COLUMN nickname VARCHAR(50) DEFAULT 'Journey 用户' NOT NULL",
    "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255)",
    "is_activated": "ALTER TABLE users ADD COLUMN is_activated BOOLEAN DEFAULT 0 NOT NULL",
    "invite_code_id": "ALTER TABLE users ADD COLUMN invite_code_id INTEGER",
    "goal": "ALTER TABLE users ADD COLUMN goal VARCHAR(20) DEFAULT '维持' NOT NULL",
    "height": "ALTER TABLE users ADD COLUMN height FLOAT",
    "weight": "ALTER TABLE users ADD COLUMN weight FLOAT"
}

PROFILE_COLUMN_SQL = {
    "nickname": "ALTER TABLE profiles ADD COLUMN nickname VARCHAR(50) DEFAULT 'Journey 用户' NOT NULL",
    "goal": "ALTER TABLE profiles ADD COLUMN goal VARCHAR(20) DEFAULT '维持' NOT NULL",
    "height": "ALTER TABLE profiles ADD COLUMN height FLOAT",
    "weight": "ALTER TABLE profiles ADD COLUMN weight FLOAT"
}

FOOD_RECORD_COLUMN_SQL = {
    "source_type": "ALTER TABLE food_records ADD COLUMN source_type VARCHAR(30) DEFAULT 'manual' NOT NULL",
    "ai_type": "ALTER TABLE food_records ADD COLUMN ai_type VARCHAR(50)",
}

ACTIVITY_RECORD_COLUMN_SQL = {
    "source_type": "ALTER TABLE activity_records ADD COLUMN source_type VARCHAR(30) DEFAULT 'manual' NOT NULL",
    "ai_type": "ALTER TABLE activity_records ADD COLUMN ai_type VARCHAR(50)",
}


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
        {"table_name": table_name}
    ).fetchone()
    return row is not None


def _column_names(connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def _add_missing_columns(connection, table_name: str, column_sql_map: dict[str, str]):
    if not _table_exists(connection, table_name):
        return

    existing = _column_names(connection, table_name)
    for column_name, alter_sql in column_sql_map.items():
        if column_name not in existing:
            connection.execute(text(alter_sql))


def _seed_invite_codes(connection):
    rows = connection.execute(
        text("SELECT COUNT(1) FROM invite_codes")
    ).fetchone()
    count = int(rows[0] or 0)

    if count > 0:
        return

    seed_codes = [
        "JOURNEY-MINT-001",
        "JOURNEY-MINT-002",
        "JOURNEY-MINT-003"
    ]

    for code in seed_codes:
        connection.execute(
            text(
                """
                INSERT INTO invite_codes
                (code, status, max_uses, used_count, created_at, updated_at)
                VALUES (:code, 'unused', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"code": code}
        )


def bootstrap_database(engine):
    with engine.begin() as connection:
        _add_missing_columns(connection, "users", USER_COLUMN_SQL)
        _add_missing_columns(connection, "profiles", PROFILE_COLUMN_SQL)
        _add_missing_columns(connection, "food_records", FOOD_RECORD_COLUMN_SQL)
        _add_missing_columns(connection, "activity_records", ACTIVITY_RECORD_COLUMN_SQL)
        _seed_invite_codes(connection)
