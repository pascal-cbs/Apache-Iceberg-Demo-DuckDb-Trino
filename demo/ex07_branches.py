"""07 - Branches: Write-Audit-Publish. Nieuwe data eerst op een branch controleren, daarna pas publiceren."""
from demo.common import console, fresh_catalog, q, titel, uitleg
from demo.data import BATCH_1, BATCH_2, ORDERS_SCHEMA


def main():
    titel("07 - Branches (Write-Audit-Publish)")
    tbl = fresh_catalog().create_table("demo.orders", schema=ORDERS_SCHEMA)
    tbl.append(BATCH_1)

    uitleg("Maak een branch 'audit' vanaf de huidige main en schrijf daar de nieuwe batch naartoe:")
    tbl.manage_snapshots().create_branch(tbl.current_snapshot().snapshot_id, "audit").commit()
    tbl.append(BATCH_2, branch="audit")
    tbl = tbl.refresh()

    main_id = tbl.snapshot_by_name("main").snapshot_id
    audit_id = tbl.snapshot_by_name("audit").snapshot_id
    uitleg("Lezers van main zien niets van de nieuwe data:")
    q(tbl, "SELECT count(*) AS main_rijen FROM {t}", snapshot_id=main_id)
    uitleg("Op de branch kun je de data auditen (hier: controle op negatieve bedragen):")
    q(tbl, "SELECT count(*) AS audit_rijen, count(*) FILTER (WHERE amount < 0) AS fout FROM {t}", snapshot_id=audit_id)

    uitleg("Audit OK -> publiceer: main verwijst nu naar de snapshot van de branch (geen data gekopieerd):")
    tbl.manage_snapshots().set_current_snapshot(snapshot_id=audit_id).commit()
    q(tbl, "SELECT count(*) AS main_rijen FROM {t}")
    tbl.manage_snapshots().remove_branch("audit").commit()
    console.print("  refs:", list(tbl.refresh().metadata.refs))


if __name__ == "__main__":
    main()
