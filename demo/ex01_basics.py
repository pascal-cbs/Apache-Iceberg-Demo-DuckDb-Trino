"""01 - Basis: tabel aanmaken, data toevoegen, bevragen met DuckDB, en wat er op schijf staat."""
from demo.common import WAREHOUSE, console, fresh_catalog, q, titel, uitleg
from demo.data import BATCH_1, BATCH_2, ORDERS_SCHEMA


def main():
    titel("01 - Basis")
    catalog = fresh_catalog()
    tbl = catalog.create_table("demo.orders", schema=ORDERS_SCHEMA)
    tbl.append(BATCH_1)
    tbl.append(BATCH_2)

    uitleg("Iceberg-tabel bevragen met DuckDB (iceberg_scan op de metadata):")
    q(tbl, "SELECT customer, count(*) AS orders, sum(amount) AS totaal FROM {t} GROUP BY 1 ORDER BY 3 DESC")

    uitleg("Op schijf: parquet-databestanden + een metadata-laag (json + avro manifests):")
    for p in sorted(WAREHOUSE.rglob("*")):
        if p.is_file() and p.name != "catalog.db":
            console.print(f"  {p.relative_to(WAREHOUSE).as_posix()}")


if __name__ == "__main__":
    main()
