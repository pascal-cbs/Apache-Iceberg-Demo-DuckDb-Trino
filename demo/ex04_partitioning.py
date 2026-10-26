"""04 - Hidden partitioning & partition evolution."""
from pyiceberg.expressions import GreaterThanOrEqual
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.transforms import IdentityTransform, MonthTransform

from demo.common import console, fresh_catalog, q, titel, toon_tabel, uitleg
from demo.data import BATCH_1, BATCH_2, ORDERS_SCHEMA, orders


def main():
    titel("04 - Partitionering")
    spec = PartitionSpec(PartitionField(source_id=5, field_id=1000, transform=MonthTransform(), name="order_month"))
    tbl = fresh_catalog().create_table("demo.orders", schema=ORDERS_SCHEMA, partition_spec=spec)
    tbl.append(BATCH_1)
    tbl.append(BATCH_2)

    uitleg("Hidden partitioning: partitie is afgeleid van order_ts (month); gebruikers filteren gewoon op order_ts.")
    uitleg("Bestanden per partitie:")
    toon_tabel(tbl.inspect.files().select(["file_path", "partition", "record_count"]).set_column(
        0, "file_path", [[p.as_py().split("/")[-2] + "/" + p.as_py().split("/")[-1][:12] for p in
                          tbl.inspect.files()["file_path"]]]))

    uitleg("Query met filter op order_ts - DuckDB/Iceberg kan het februari-bestand overslaan (partition pruning):")
    q(tbl, "SELECT order_id, order_ts FROM {t} WHERE order_ts >= TIMESTAMPTZ '2025-02-01' ORDER BY 1")
    plan = tbl.scan(row_filter=GreaterThanOrEqual("order_ts", "2025-02-01T00:00:00+00:00")).plan_files()
    console.print(f"  pyiceberg plant {len(list(plan))} van {len(tbl.inspect.files())} bestanden")

    uitleg("Partition evolution: vanaf nu ook op product partitioneren. Oude data blijft in het oude layout.")
    with tbl.update_spec() as u:
        u.add_field("product", IdentityTransform(), "product")
    tbl.append(orders(6, [("erin", "laptop", 1300.0, "2025-03-03"), ("frank", "muis", 20.0, "2025-03-04")]))
    console.print("  partition specs:", {s.spec_id: str(s) for s in tbl.metadata.partition_specs})
    toon_tabel(tbl.inspect.files().select(["spec_id", "partition", "record_count"]))
    q(tbl, "SELECT count(*) AS aantal, sum(amount) AS omzet FROM {t}")


if __name__ == "__main__":
    main()
