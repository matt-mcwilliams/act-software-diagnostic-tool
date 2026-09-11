from pathlib import Path

from app.migrations import migration_checksum, migration_files, split_sql


def test_split_sql_preserves_semicolons_inside_strings() -> None:
    statements = split_sql("CREATE TABLE example (name text); INSERT INTO example VALUES ('a;b');")

    assert statements == [
        "CREATE TABLE example (name text)",
        "INSERT INTO example VALUES ('a;b')",
    ]


def test_domain_migration_manifest_is_stable() -> None:
    files = migration_files()

    assert [path.name for path in files] == [
        "0001_domain_schema.sql",
        "0002_import_batches.sql",
        "0003_content_source_identity.sql",
        "0004_practice_session_link.sql",
    ]
    assert all(len(migration_checksum(path)) == 64 for path in files)
    assert Path(files[0]).read_text(encoding="utf-8").count("CREATE TABLE") >= 20
