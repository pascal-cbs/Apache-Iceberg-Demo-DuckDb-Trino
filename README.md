# Apache Iceberg demo met DuckDB

Lokale demo's (geen cloud, geen Spark) van wat Apache Iceberg bijzonder maakt.
Schrijven/beheren gaat met **PyIceberg** (SQLite-catalog + parquet-bestanden in `./warehouse`),
bevragen gaat met **DuckDB** via de `iceberg`-extensie (`iceberg_scan`).

## Starten

```bash
uv sync
uv run python -m demo.run_all          # alles
uv run python -m demo.ex02_time_travel # of één voorbeeld
```

De eerste keer downloadt DuckDB de `iceberg`-extensie (internet nodig). Lukt dat niet, dan valt
`demo/common.py` terug op PyIceberg -> Arrow -> DuckDB (alleen time-travel per tijdstip werkt dan niet).
Elke demo begint met een schone `warehouse/`-map.

## Voorbeelden

| Script | Functionaliteit |
|---|---|
| `ex01_basics` | Tabel maken, appends, SQL via DuckDB, bestandsstructuur (data + metadata/manifests) |
| `ex02_time_travel` | Snapshots, query op snapshot-id/tijdstip, tags, rollback |
| `ex03_schema_evolution` | Kolom toevoegen/hernoemen/verbreden/verwijderen zonder herschrijven (field-ids) |
| `ex04_partitioning` | Hidden partitioning (`month(order_ts)`), partition pruning, partition evolution |
| `ex05_row_level` | Delete, upsert (merge), overwrite met filter; atomaire commits |
| `ex06_metadata_maintenance` | `inspect`-metadatatabellen, compactie, snapshots expiren |
| `ex07_branches` | Branches en Write-Audit-Publish |

## Structuur

- `demo/common.py` - catalog, `q(table, sql)` helper (`{t}` = de Iceberg-tabel)
- `demo/data.py` - schema en voorbeeldbestellingen

## Multi-engine variant: PyIceberg + DuckDB + Trino (Docker)

`ex08_multi_engine` laat zien dat één Iceberg-tabel door meerdere engines tegelijk gebruikt wordt.

```bash
docker compose up -d          # S3 (RustFS), Iceberg REST-catalog, Trino  (Trino heeft ~30s nodig)
uv run python -m demo.ex08_multi_engine
docker compose down           # stoppen (-v wist ook de data)
```

| Component | Poort | Rol |
|---|---|---|
| RustFS (S3) | 9000 / 9001 (console, admin/password) | S3-opslag, bucket `warehouse` (MinIO-image bestaat niet meer op Docker Hub) |
| iceberg-rest-fixture | 8181 | Iceberg REST-catalog (in-memory; bij herstart is de catalog leeg) |
| Trino | 8080 | SQL-engine, catalog `iceberg` (`trino/etc/catalog/iceberg.properties`) |

PyIceberg schrijft, DuckDB leest via `iceberg_scan('s3://...')`, Trino doet INSERT/UPDATE/DELETE/MERGE,
ALTER TABLE, time travel, `$snapshots`/`$files` en `optimize` op dezelfde tabel. Code: `demo/engines.py`.

### Branches in de multi-engine variant (`ex09_multi_engine_branches`)

Write-Audit-Publish met drie engines: PyIceberg **schrijft** naar een branch `audit`, Trino **controleert**
die branch met SQL (`FOR VERSION AS OF 'audit'`), DuckDB leest dezelfde branch via de snapshot-id.
Ronde 1 laat een foute batch zien (dubbele id's, negatief bedrag): afgekeurd, branch weggegooid, `main` nooit aangeraakt.
Ronde 2 een correcte batch: goedgekeurd en gepubliceerd door `main` naar de snapshot van de branch te laten wijzen.
Bij elke stap toont een tabel hoeveel rijen `main` en `audit` per engine bevatten.

Publish met Trino in plaats van PyIceberg: `uv run python -m demo.ex09_multi_engine_branches --publish-met trino`.
Trino 476 heeft geen branch-DDL; de omweg is `ALTER TABLE ... EXECUTE rollback_to_snapshot(<branch-snapshot>)`.
Dat werkt, maar is bedoeld voor terugdraaien en geen gedocumenteerd gebruik voor vooruit publiceren.

## Licentie

MIT - zie [LICENSE](LICENSE).
