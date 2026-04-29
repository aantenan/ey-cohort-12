"""Print SQLite DDL for local.db — run from backend/: python scripts/dump_sqlite_schema.py"""

import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DB = HERE / "local.db"


def main() -> None:
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for name, sql in rows:
        if sql:
            print(sql.strip())
            print()
    print("--- INDEXES ---")
    for (sql,) in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ):
        print(sql.strip())
        print()


if __name__ == "__main__":
    main()
