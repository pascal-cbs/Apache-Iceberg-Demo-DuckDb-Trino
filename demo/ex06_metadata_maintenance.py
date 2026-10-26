"""06 - Metadata-tabellen en onderhoud: bestanden compacteren en oude snapshots opruimen."""
from datetime import datetime, timezone

from demo.common import WAREHOUSE, console, fresh_catalog, q, titel, toon_tabel, uitleg
from demo.data import ORDERS_SCHEMA, orders


def parquet_files() -> int:
    return len(list(WAREHOUSE.rglob("*.parquet")))


def main():
    titel("06 - Metadata & onderhoud")
    tbl = fresh_catalog().create_table("demo.orders", schema=ORDERS_SCHEMA)
    for i in range(5):  # veel kleine writes -> veel kleine bestanden
        tbl.append(orders(i * 10, [("klant", "item", 10.0 + i, "2025-01-01")]))

    uitleg("Iceberg beheert eigen metadata die je als tabel kunt bevragen (inspect):")
    toon_tabel(tbl.inspect.snapshots().select(["snapshot_id", "operation"]))
    toon_tabel(tbl.inspect.files().select(["record_count", "file_size_in_bytes"]))
    console.print(f"  parquet-bestanden op schijf: {parquet_files()}")

    uitleg("Compactie: herschrijf 5 kleine bestanden naar 1 (data identiek, nieuwe snapshot):")
    data = tbl.scan().to_arrow()
    tbl.overwrite(data)
    console.print(f"  actieve databestanden: {len(tbl.inspect.files())}, op schijf (incl. oude): {parquet_files()}")

    uitleg("Snapshots opruimen (expire) - oude versies zijn dan niet meer te time-travellen:")
    tbl.maintenance.expire_snapshots().older_than(datetime.now(timezone.utc)).commit()
    console.print(f"  snapshots over: {len(tbl.refresh().snapshots())}")
    q(tbl, "SELECT count(*) AS aantal FROM {t}")
    uitleg("Let op: expire verwijdert metadata-referenties; fysieke orphan-bestanden ruim je op met een aparte job.")


if __name__ == "__main__":
    main()
