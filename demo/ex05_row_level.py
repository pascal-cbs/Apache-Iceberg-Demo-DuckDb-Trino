"""05 - Row-level operaties: delete, overwrite, upsert (merge) - ACID op een bestandsformaat."""
import pyarrow as pa

from demo.common import fresh_catalog, q, titel, toon_tabel, uitleg
from demo.data import BATCH_1, BATCH_2, ORDERS_SCHEMA, orders


def main():
    titel("05 - Delete, overwrite & upsert")
    tbl = fresh_catalog().create_table("demo.orders", schema=ORDERS_SCHEMA)
    tbl.append(BATCH_1)
    tbl.append(BATCH_2)

    uitleg("DELETE met predicaat:")
    tbl.delete("amount < 50")
    q(tbl, "SELECT order_id, customer, amount FROM {t} ORDER BY 1")

    uitleg("UPSERT (merge): order 1 krijgt korting, order 10 is nieuw:")
    wijziging = orders(1, [("alice", "laptop", 999.0, "2025-01-05")]).to_pylist() + \
        orders(10, [("gina", "webcam", 60.0, "2025-03-10")]).to_pylist()
    res = tbl.upsert(pa.Table.from_pylist(wijziging, schema=tbl.schema().as_arrow()), join_cols=["order_id"])
    print(f"  updated={res.rows_updated} inserted={res.rows_inserted}")
    q(tbl, "SELECT order_id, customer, amount FROM {t} ORDER BY 1")

    uitleg("OVERWRITE met filter: alle rijen van alice vervangen:")
    tbl.overwrite(orders(20, [("alice", "tablet", 450.0, "2025-04-01")]), overwrite_filter="customer = 'alice'")
    q(tbl, "SELECT order_id, customer, product FROM {t} ORDER BY 1")

    uitleg("Elke stap is een atomaire commit - de snapshotgeschiedenis:")
    toon_tabel(tbl.inspect.snapshots().select(["snapshot_id", "operation"]).append_column(
        "added/deleted records", pa.array([
            f"+{dict(s['summary']).get('added-records', 0)} / -{dict(s['summary']).get('deleted-records', 0)}"
            for s in tbl.inspect.snapshots().to_pylist()])))


if __name__ == "__main__":
    main()
