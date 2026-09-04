from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def table_definition(schema: str, table_name: str) -> str:
    start = schema.index(f"CREATE TABLE IF NOT EXISTS {table_name}")
    end = schema.index("\n);", start)
    return schema[start:end]


def test_fresh_schema_matches_runtime_upsert_constraints() -> None:
    # Given
    schema = (ROOT / "postgres/initdb/02-schema.sql").read_text()

    # When
    whitelist = table_definition(schema, "whitelist_ips")
    blacklist = table_definition(schema, "blacklist_ips")

    # Then
    assert "is_active BOOLEAN NOT NULL DEFAULT TRUE" in whitelist
    assert "UNIQUE(ip_address)" in whitelist
    assert "UNIQUE(ip_address, source)" in blacklist


def test_upgrade_migration_adds_whitelist_activity_and_upsert_indexes() -> None:
    # Given
    migration_path = ROOT / "postgres/migrations/007_align_ip_schema_contracts.sql"

    # When
    migration = migration_path.read_text()

    # Then
    assert "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE" in migration
    assert "ALTER COLUMN is_active SET NOT NULL" in migration
    assert "ALTER TABLE blacklist_ips" in migration
    assert "ON whitelist_ips(ip_address)" in migration
    assert "ON blacklist_ips(ip_address, source)" in migration


def test_bootstrap_owner_applies_runtime_schema_before_grants() -> None:
    role_configurator = (ROOT / "postgres/configure-runtime-roles.sh").read_text()
    monitoring_migration = (ROOT / "postgres/migrations/008_add_regtech_monitoring.sql").read_text()

    assert "007_align_ip_schema_contracts.sql" in role_configurator
    assert "008_add_regtech_monitoring.sql" in role_configurator
    assert "CREATE TABLE IF NOT EXISTS regtech_monitoring" in monitoring_migration
    assert "CREATE TABLE IF NOT EXISTS regtech_alerts" in monitoring_migration
