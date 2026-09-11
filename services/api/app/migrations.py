import argparse
import hashlib
from pathlib import Path

_MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_schema_migrations (
  version text PRIMARY KEY,
  checksum text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def migration_directory() -> Path:
    return Path(__file__).resolve().parents[1] / "migrations"


def migration_files(directory: Path | None = None) -> list[Path]:
    root = directory or migration_directory()
    return sorted(path for path in root.glob("*.sql") if path.is_file())


def split_sql(source: str) -> list[str]:
    """Split the current migration format without requiring a SQL parser."""
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    index = 0

    while index < len(source):
        character = source[index]
        if character == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif character == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if character == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(character)
        index += 1

    statement = "".join(buffer).strip()
    if statement:
        statements.append(statement)
    return statements


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_migrations(database_url: str, directory: Path | None = None) -> list[str]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required to apply API migrations") from exc

    applied: list[str] = []
    files = migration_files(directory)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(_MIGRATION_TABLE_SQL)
            for path in files:
                version = path.name
                checksum = migration_checksum(path)
                cursor.execute(
                    "SELECT checksum FROM api_schema_migrations WHERE version = %s",
                    (version,),
                )
                existing = cursor.fetchone()
                if existing:
                    if existing[0] != checksum:
                        raise RuntimeError(f"Migration {version} changed after it was applied")
                    continue

                for statement in split_sql(path.read_text(encoding="utf-8")):
                    cursor.execute(statement)
                cursor.execute(
                    "INSERT INTO api_schema_migrations (version, checksum) VALUES (%s, %s)",
                    (version, checksum),
                )
                applied.append(version)
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply ACT Adaptive API migrations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List migration files and checksums without connecting to PostgreSQL",
    )
    args = parser.parse_args()
    files = migration_files()
    if args.dry_run:
        for path in files:
            print(f"{path.name} {migration_checksum(path)}")
        return

    from .settings import get_settings

    database_url = get_settings().database_url
    if not database_url:
        raise SystemExit("ACT_API_DATABASE_URL is required unless --dry-run is used")
    applied = apply_migrations(database_url)
    print(f"Applied {len(applied)} migration(s): {', '.join(applied) or 'none'}")


if __name__ == "__main__":
    main()
