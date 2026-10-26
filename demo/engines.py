"""Multi-engine setup: PyIceberg (REST-catalog) + DuckDB (S3) + Trino, allemaal op dezelfde S3-tabellen."""
from __future__ import annotations

import duckdb
import pyarrow as pa
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.exceptions import NoSuchTableError
from pyiceberg.table import Table
from trino.dbapi import connect

from demo.common import console, toon_tabel

S3 = {"endpoint": "http://localhost:9000", "key": "admin", "secret": "password", "region": "us-east-1"}


def rest_catalog() -> RestCatalog:
    catalog = RestCatalog(
        "rest",
        uri="http://localhost:8181",
        **{
            "s3.endpoint": S3["endpoint"],
            "s3.access-key-id": S3["key"],
            "s3.secret-access-key": S3["secret"],
            "s3.region": S3["region"],
            "s3.path-style-access": "true",
        },
    )
    catalog.create_namespace_if_not_exists("demo")
    return catalog


def drop_if_exists(catalog: RestCatalog, name: str) -> None:
    try:
        catalog.drop_table(name)
    except NoSuchTableError:
        pass


def duck(table: Table, sql: str, *, snapshot_id: int | None = None, toon: bool = True) -> pa.Table:
    """DuckDB leest de Iceberg-tabel rechtstreeks van S3. `{t}` = de tabel."""
    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg; INSTALL httpfs; LOAD httpfs;")
    con.execute(
        f"CREATE SECRET (TYPE S3, KEY_ID '{S3['key']}', SECRET '{S3['secret']}', REGION '{S3['region']}', "
        "ENDPOINT 'localhost:9000', URL_STYLE 'path', USE_SSL false)"
    )
    table = table.refresh()
    extra = f", snapshot_from_id={snapshot_id}" if snapshot_id else ""
    result = con.sql(sql.replace("{t}", f"iceberg_scan('{table.metadata_location}'{extra})")).to_arrow_table()
    if toon:
        console.print(f"[magenta]DuckDB>[/magenta] {sql.replace('{t}', 'orders')}", soft_wrap=True)
        toon_tabel(result)
    return result


def trino(sql: str, *, toon: bool = True) -> pa.Table:
    """Voer SQL uit op Trino (catalog `iceberg`, schema `demo`)."""
    conn = connect(host="localhost", port=8080, user="demo", catalog="iceberg", schema="demo")
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    names = [d[0] for d in cur.description] if cur.description else []
    result = pa.Table.from_pylist([dict(zip(names, r)) for r in rows]) if rows else pa.table({n: [] for n in names})
    if toon:
        console.print(f"[yellow]Trino>[/yellow] {sql}", soft_wrap=True)
        if names:
            toon_tabel(result)
    return result
