"""08 - Meerdere engines op één tabel: PyIceberg, DuckDB en Trino delen dezelfde Iceberg-tabel.

Vereist de docker-stack:  docker compose up -d
"""
from demo.common import titel, uitleg
from demo.data import BATCH_1, ORDERS_SCHEMA
from demo.engines import drop_if_exists, duck, rest_catalog, trino


def main():
    titel("08 - PyIceberg + DuckDB + Trino op dezelfde tabel")
    catalog = rest_catalog()
    drop_if_exists(catalog, "demo.orders")
    tbl = catalog.create_table("demo.orders", schema=ORDERS_SCHEMA)

    uitleg("1) PyIceberg schrijft 3 rijen naar S3 (via de REST-catalog):")
    tbl.append(BATCH_1)

    uitleg("2) DuckDB en Trino lezen exact dezelfde data:")
    duck(tbl, "SELECT count(*) AS aantal, sum(amount) AS omzet FROM {t}")
    trino("SELECT count(*) AS aantal, sum(amount) AS omzet FROM orders")

    uitleg("3) Trino schrijft: INSERT, UPDATE, DELETE en MERGE zijn gewone SQL:")
    trino("INSERT INTO orders VALUES (4, 'dave', 'laptop', 1150.0, TIMESTAMP '2025-02-14 00:00:00.000000 UTC')")
    trino("UPDATE orders SET amount = 1000.0 WHERE order_id = 1")
    trino("DELETE FROM orders WHERE customer = 'bob'")
    trino("""MERGE INTO orders t USING (VALUES (3, 'carol', 'monitor', 250.0), (9, 'hans', 'dock', 90.0))
             AS s(order_id, customer, product, amount) ON t.order_id = s.order_id
             WHEN MATCHED THEN UPDATE SET amount = s.amount
             WHEN NOT MATCHED THEN INSERT (order_id, customer, product, amount)
                  VALUES (s.order_id, s.customer, s.product, s.amount)""", toon=False)

    uitleg("4) PyIceberg en DuckDB zien meteen de wijzigingen van Trino:")
    duck(tbl, "SELECT order_id, customer, amount FROM {t} ORDER BY 1")
    print(f"  PyIceberg ziet {len(tbl.refresh().scan().to_arrow())} rijen en {len(tbl.snapshots())} snapshots")

    uitleg("5) Schema-evolutie via Trino, daarna direct zichtbaar in DuckDB:")
    trino("ALTER TABLE orders ADD COLUMN land varchar", toon=False)
    trino("UPDATE orders SET land = 'NL' WHERE customer IN ('alice', 'carol')", toon=False)
    duck(tbl, "SELECT order_id, customer, land FROM {t} ORDER BY 1")

    uitleg("6) Time travel en metadata in Trino:")
    snaps = trino('SELECT snapshot_id, operation FROM "orders$snapshots" ORDER BY committed_at')
    eerste = snaps["snapshot_id"][0].as_py()
    trino(f"SELECT count(*) AS aantal FROM orders FOR VERSION AS OF {eerste}")

    uitleg("7) Onderhoud via Trino: kleine bestanden samenvoegen:")
    trino("ALTER TABLE orders EXECUTE optimize", toon=False)
    trino('SELECT count(*) AS actieve_bestanden FROM "orders$files"')


if __name__ == "__main__":
    main()
