"""09 - Branches in de multi-engine opzet: Write-Audit-Publish met PyIceberg, DuckDB en Trino.

Verhaal: een ETL-job (PyIceberg) laadt een nieuwe batch.
  WRITE   - de batch gaat naar een aparte branch 'audit'; main blijft ongemoeid.
  AUDIT   - een andere engine (Trino) controleert de branch met SQL.
  PUBLISH - alleen bij goedkeuring verwijst main naar de branch. Anders gooien we de branch weg.

Een branch is niets anders dan een naam die naar een snapshot wijst; er wordt geen data gekopieerd.
Publish kan met PyIceberg (standaard) of met Trino:
  uv run python -m demo.ex09_multi_engine_branches                      # publish met PyIceberg
  uv run python -m demo.ex09_multi_engine_branches --publish-met trino  # publish met Trino

Vereist de docker-stack:  docker compose up -d
"""
import sys

from rich.table import Table as RichTable

from demo.common import console, titel, uitleg
from demo.data import BATCH_1, ORDERS_SCHEMA, orders
from demo.engines import drop_if_exists, duck, rest_catalog, trino


def wie_ziet_wat(tbl, stap: str) -> None:
    """Toont per engine hoeveel rijen main en de branch 'audit' bevatten."""
    tbl = tbl.refresh()
    refs = tbl.metadata.refs
    rt = RichTable(title=f"Wie ziet wat - {stap}", header_style="bold")
    for kolom in ("engine", "main", "audit"):
        rt.add_column(kolom)

    def tel_duck(snapshot_id=None):
        return str(duck(tbl, "SELECT count(*) AS n FROM {t}", snapshot_id=snapshot_id, toon=False)["n"][0])

    def tel_trino(branch=None):
        voor = f" FOR VERSION AS OF '{branch}'" if branch else ""
        return str(trino(f"SELECT count(*) AS n FROM orders{voor}", toon=False)["n"][0])

    audit = "audit" in refs
    rt.add_row("DuckDB (snapshot-id)", tel_duck(refs["main"].snapshot_id), tel_duck(refs["audit"].snapshot_id) if audit else "-")
    rt.add_row("Trino (FOR VERSION AS OF)", tel_trino(), tel_trino("audit") if audit else "-")
    console.print(rt)


def audit_met_trino() -> tuple[bool, str]:
    """Kwaliteitscontrole in SQL op de branch: geen negatieve bedragen, geen dubbele order_id's."""
    res = trino("""
        SELECT count_if(amount < 0) AS negatief,
               count(*) - count(DISTINCT order_id) AS dubbel
        FROM orders FOR VERSION AS OF 'audit'""")
    negatief, dubbel = res["negatief"][0].as_py(), res["dubbel"][0].as_py()
    return negatief == 0 and dubbel == 0, f"{negatief} negatieve bedragen, {dubbel} dubbele order_id's"


def main():
    titel("09 - Branches in de multi-engine variant (Write-Audit-Publish)")
    catalog = rest_catalog()
    drop_if_exists(catalog, "demo.orders")
    tbl = catalog.create_table("demo.orders", schema=ORDERS_SCHEMA)
    tbl.append(BATCH_1)

    uitleg("Beginsituatie: productie-tabel (main) met 3 rijen.")
    wie_ziet_wat(tbl, "begin")

    # ---------------------------------------------------------------- ronde 1: foute batch
    titel("Ronde 1 - een foute batch")
    uitleg("WRITE: PyIceberg maakt branch 'audit' en schrijft daar een batch met fouten "
           "(order 2 en 3 bestaan al, order 4 heeft een negatief bedrag):")
    tbl.manage_snapshots().create_branch(tbl.current_snapshot().snapshot_id, "audit").commit()
    foute_batch = orders(2, [("bob", "muis", 25.0, "2025-02-01"), ("carol", "monitor", 300.0, "2025-02-02"),
                             ("y", "kabel", -5.0, "2025-02-03")])
    tbl.append(foute_batch, branch="audit")
    wie_ziet_wat(tbl, "na write op de branch  -> main is nog 3, audit is 6")

    uitleg("AUDIT: Trino controleert de branch (andere engine dan de schrijver):")
    ok, uitslag = audit_met_trino()
    console.print(f"  Resultaat: {'[green]OK[/green]' if ok else '[red]AFGEKEURD[/red]'} ({uitslag})")

    if not ok:
        uitleg("Afgekeurd -> branch weggooien. Niemand die main leest heeft ooit iets van de foute data gezien:")
        tbl.manage_snapshots().remove_branch("audit").commit()
        wie_ziet_wat(tbl, "na weggooien branch")

    # ---------------------------------------------------------------- ronde 2: goede batch
    titel("Ronde 2 - de gecorrigeerde batch")
    uitleg("WRITE: nieuwe branch, nu met een correcte batch:")
    tbl = tbl.refresh()
    tbl.manage_snapshots().create_branch(tbl.current_snapshot().snapshot_id, "audit").commit()
    tbl.append(orders(4, [("dave", "laptop", 1150.0, "2025-02-14"), ("erin", "kabel", 10.0, "2025-02-15")]),
               branch="audit")
    wie_ziet_wat(tbl, "na write op de branch")

    uitleg("AUDIT: dezelfde controle in Trino:")
    ok, uitslag = audit_met_trino()
    console.print(f"  Resultaat: {'[green]OK[/green]' if ok else '[red]AFGEKEURD[/red]'} ({uitslag})")

    if ok:
        tbl = tbl.refresh()
        audit_snapshot = tbl.metadata.refs["audit"].snapshot_id
        if "trino" in sys.argv[1:]:
            uitleg("PUBLISH met Trino: Trino 476 heeft geen branch-DDL (geen FAST FORWARD). Omweg: de tabelprocedure "
                   "rollback_to_snapshot zet main op de snapshot van de branch. Let op: die procedure is bedoeld om "
                   "terug te gaan; vooruit werkt in deze versie, maar is geen gedocumenteerd gebruik.")
            trino(f"ALTER TABLE orders EXECUTE rollback_to_snapshot({audit_snapshot})")
        else:
            uitleg("PUBLISH met PyIceberg: main wordt naar de snapshot van de branch gezet (een metadata-wijziging, "
                   "geen datakopie). Alle engines zien de nieuwe data in een atomaire stap:")
            tbl.manage_snapshots().set_current_snapshot(snapshot_id=audit_snapshot).commit()
        wie_ziet_wat(tbl, "na publish")
        uitleg("De branch zelf beheren kan alleen met PyIceberg (Trino kent geen DROP BRANCH):")
        tbl.refresh().manage_snapshots().remove_branch("audit").commit()

    uitleg("Opruimen: de branch is verwijderd; main bevat de gepubliceerde batch. Snapshotgeschiedenis in Trino:")
    trino('SELECT snapshot_id, operation, parent_id FROM "orders$snapshots" ORDER BY committed_at')
    trino('SELECT name, type, snapshot_id FROM "orders$refs"')


if __name__ == "__main__":
    main()
