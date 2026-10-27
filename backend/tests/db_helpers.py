import os
import random
import string
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg2


def rand_dbname(prefix: str = "seekr_test_") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}{suffix}"


def normalise_db_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname == "db":
        return urlunparse(parsed._replace(netloc=parsed.netloc.replace("db", "localhost", 1)))
    return url


def to_sync_pg_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def replace_db_in_url(url: str, new_db: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=f"/{new_db}"))


def get_admin_url(base_db_url: str) -> str:
    return replace_db_in_url(to_sync_pg_url(base_db_url), "postgres")


def psql_scalar(db_url: str, sql: str, params=None):
    conn = psycopg2.connect(to_sync_pg_url(db_url))
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def assert_table_exists(db_url: str, table: str) -> None:
    exists = psql_scalar(db_url, "SELECT to_regclass(%s) IS NOT NULL;", (f"public.{table}",))
    assert exists is True, f"Expected table public.{table} to exist"


def assert_column_exists(db_url: str, table: str, column: str) -> None:
    exists = psql_scalar(
        db_url,
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
        );
        """,
        (table, column),
    )
    assert exists is True, f"Expected column {column} on {table} to exist"


def assert_index_exists(
    db_url: str, table: str, index_name: str, expected_cols_snippet: str
) -> None:
    indexdef = psql_scalar(
        db_url,
        """
        SELECT indexdef
        FROM pg_indexes
        WHERE schemaname='public' AND tablename=%s AND indexname=%s;
        """,
        (table, index_name),
    )
    assert indexdef is not None, f"Expected index {index_name} on {table} to exist"
    assert (
        expected_cols_snippet in indexdef
    ), f"Index {index_name} definition unexpected: {indexdef}"


def assert_fk_on_delete_cascade(db_url: str, child_table: str, parent_table: str) -> None:
    cascade = psql_scalar(
        db_url,
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class child  ON child.oid  = c.conrelid
            JOIN pg_class parent ON parent.oid = c.confrelid
            WHERE c.contype = 'f'
              AND child.relname  = %s
              AND parent.relname = %s
              AND c.confdeltype  = 'c'
        );
        """,
        (child_table, parent_table),
    )
    assert cascade is True, f"Expected FK {child_table} -> {parent_table} with ON DELETE CASCADE"


def assert_alembic_version_present(db_url: str) -> None:
    ver = psql_scalar(db_url, "SELECT version_num FROM alembic_version LIMIT 1;")
    assert ver is not None and len(ver) > 0, "Expected alembic_version to contain a revision id"


def run_alembic_upgrade(db_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(f"alembic.ini not found at {alembic_ini}. Run tests from backend root.")

    old_env = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = db_url
    try:
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", db_url)

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(command.upgrade, cfg, "head")
            future.result()
    finally:
        if old_env is not None:
            os.environ["ALEMBIC_DATABASE_URL"] = old_env
        else:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
