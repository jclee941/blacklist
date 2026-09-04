import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "postgres/configure-runtime-roles.sh"


def test_collector_role_has_only_collection_table_permissions() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "BEGIN;" in source
    assert "REVOKE ALL PRIVILEGES ON ALL TABLES" in source
    assert 'REVOKE CREATE ON SCHEMA public FROM :"app_user", :"collector_user"' in source
    assert "GRANT SELECT ON TABLE collection_credentials" in source
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE blacklist_ips" in source
    assert "system_settings TO" not in source
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE credentials" not in source
    assert "collection_status_id_seq" in source


@pytest.mark.parametrize(
    ("owner", "database_owner", "app_user", "collector_user"),
    (
        ("postgres", "blacklist_owner", "postgres", "blacklist_collector"),
        ("postgres", "blacklist_owner", "blacklist_app", "postgres"),
        ("postgres", "blacklist_owner", "blacklist_runtime", "blacklist_runtime"),
        ("postgres", "postgres", "blacklist_app", "blacklist_collector"),
    ),
)
def test_role_configuration_rejects_name_collisions(
    owner: str,
    database_owner: str,
    app_user: str,
    collector_user: str,
) -> None:
    environment = dict(
        os.environ,
        POSTGRES_DB="blacklist",
        POSTGRES_USER=owner,
        POSTGRES_PASSWORD="owner-password",
        DB_OWNER_ROLE=database_owner,
        APP_DB_USER=app_user,
        APP_DB_PASSWORD="app-password",
        COLLECTOR_DB_USER=collector_user,
        COLLECTOR_DB_PASSWORD="collector-password",
    )

    result = subprocess.run(
        ["sh", str(SCRIPT)],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 2
    assert "role names must be unique" in result.stderr
