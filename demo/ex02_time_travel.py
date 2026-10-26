"""02 - Snapshots & time travel: elke write maakt een nieuwe snapshot; oude versies blijven leesbaar."""
import time

from demo.common import console, fresh_catalog, nu, q, titel, toon_tabel, uitleg
from demo.data import BATCH_1, BATCH_2, ORDERS_SCHEMA


def main():
    titel("02 - Time travel & rollback")
    tbl = fresh_catalog().create_table("demo.orders", schema=ORDERS_SCHEMA)

    tbl.append(BATCH_1)
    tijd_na_batch1 = nu()
    time.sleep(0.05)
    tbl.append(BATCH_2)
    tbl.delete("customer = 'bob'")

    uitleg("Elke wijziging is een snapshot (ook de delete):")
    toon_tabel(tbl.inspect.snapshots().select(["snapshot_id", "committed_at", "operation"]))
    snaps = tbl.inspect.snapshots().to_pylist()
    eerste = snaps[0]["snapshot_id"]

    uitleg("Huidige staat:")
    q(tbl, "SELECT count(*) AS aantal FROM {t}")
    uitleg("Op snapshot-id (na batch 1):")
    q(tbl, "SELECT count(*) AS aantal FROM {t}", snapshot_id=eerste)
    uitleg("Op tijdstip (vlak na batch 1):")
    q(tbl, "SELECT count(*) AS aantal FROM {t}", as_of=tijd_na_batch1)

    uitleg("Tags geven een snapshot een leesbare naam:")
    tbl.manage_snapshots().create_tag(eerste, "na-batch-1").commit()
    console.print("  refs:", {k: v.snapshot_ref_type for k, v in tbl.refresh().metadata.refs.items()})

    uitleg("Rollback naar de eerste snapshot (de data is niet verwijderd, alleen de pointer verschuift):")
    tbl.manage_snapshots().rollback_to_snapshot(eerste).commit()
    q(tbl, "SELECT count(*) AS aantal FROM {t}")


if __name__ == "__main__":
    main()
