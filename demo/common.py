"""Gedeelde hulpfuncties: lokale Iceberg-catalog (SQLite + bestanden) en DuckDB-queries."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import duckdb
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.table import Table
from rich.console import Console
from rich.table import Table as RichTable

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "warehouse"
console = Console()

_duck_state = {"iceberg": None}
_vorige: list[SqlCatalog] = []


def titel(tekst: str) -> None:
    console.rule(f"[bold cyan]{tekst}")


def uitleg(tekst: str) -> None:
    console.print(f"[dim]{tekst}[/dim]")


def fresh_catalog() -> SqlCatalog:
    """Maakt een schone catalog. Metadata-pointers staan in SQLite, data + metadata als bestanden."""
    for oud in _vorige:  # Windows: SQLite-bestand moet eerst losgelaten worden
        oud.engine.dispose()
    _vorige.clear()
    shutil.rmtree(WAREHOUSE, ignore_errors=True)
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    catalog = SqlCatalog(
        "demo",
        uri=f"sqlite:///{(WAREHOUSE / 'catalog.db').as_posix()}",
        warehouse=WAREHOUSE.as_posix(),
    )
    catalog.create_namespace("demo")
    _vorige.append(catalog)
    return catalog


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    if _duck_state["iceberg"] is None:
        try:
            con.execute("INSTALL iceberg; LOAD iceberg;")
            _duck_state["iceberg"] = True
        except Exception:
            _duck_state["iceberg"] = False
            uitleg("(DuckDB iceberg-extensie niet beschikbaar; fallback via pyiceberg -> Arrow)")
    elif _duck_state["iceberg"]:
        con.execute("LOAD iceberg;")
    return con


def _local_path(location: str) -> str:
    if location.startswith("file:"):
        return Path(url2pathname(urlparse(location).path)).as_posix()
    return location


def q(table: Table, sql: str, *, snapshot_id: int | None = None, as_of: datetime | None = None,
      toon: bool = True) -> pa.Table:
    """Draai DuckDB-SQL op een Iceberg-tabel. Gebruik `{t}` als tabelnaam in de query."""
    con = _con()
    table = table.refresh() if hasattr(table, "refresh") else table
    if _duck_state["iceberg"]:
        args = [f"'{_local_path(table.metadata_location)}'"]
        if snapshot_id is not None:
            args.append(f"snapshot_from_id={snapshot_id}")
        if as_of is not None:
            args.append(f"snapshot_from_timestamp='{as_of.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')}'::TIMESTAMP")
        source = f"iceberg_scan({', '.join(args)})"
        result = con.sql(sql.replace("{t}", source)).to_arrow_table()
    else:
        scan = table.scan(snapshot_id=snapshot_id) if snapshot_id else table.scan()
        con.register("t", scan.to_arrow())
        result = con.sql(sql.replace("{t}", "t")).to_arrow_table()
    if toon:
        console.print(f"[green]SQL>[/green] {sql.replace(chr(123)+'t'+chr(125), table.name()[-1])}", soft_wrap=True)
        toon_tabel(result)
    return result


def toon_tabel(data: pa.Table) -> None:
    rt = RichTable(header_style="bold")
    for naam in data.column_names:
        rt.add_column(naam)
    for rij in data.to_pylist():
        rt.add_row(*[str(v) for v in rij.values()])
    console.print(rt)


def nu() -> datetime:
    return datetime.now(timezone.utc)
