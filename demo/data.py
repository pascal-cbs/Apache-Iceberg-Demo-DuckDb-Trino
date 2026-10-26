"""Voorbeelddata: bestellingen van een kleine webshop."""
from datetime import datetime, timezone

import pyarrow as pa
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, LongType, NestedField, StringType, TimestamptzType

ORDERS_SCHEMA = Schema(
    NestedField(1, "order_id", LongType(), required=True),
    NestedField(2, "customer", StringType(), required=False),
    NestedField(3, "product", StringType(), required=False),
    NestedField(4, "amount", DoubleType(), required=False),
    NestedField(5, "order_ts", TimestamptzType(), required=False),
)

ARROW_SCHEMA = pa.schema([
    pa.field("order_id", pa.int64(), nullable=False),
    pa.field("customer", pa.string()),
    pa.field("product", pa.string()),
    pa.field("amount", pa.float64()),
    pa.field("order_ts", pa.timestamp("us", tz="UTC")),
])


def orders(start_id: int, rows: list[tuple]) -> pa.Table:
    """rows: (customer, product, amount, 'YYYY-MM-DD')"""
    return pa.Table.from_pylist(
        [
            {"order_id": start_id + i, "customer": c, "product": p, "amount": a,
             "order_ts": datetime.fromisoformat(d).replace(tzinfo=timezone.utc)}
            for i, (c, p, a, d) in enumerate(rows)
        ],
        schema=ARROW_SCHEMA,
    )


BATCH_1 = orders(1, [
    ("alice", "laptop", 1200.0, "2025-01-05"),
    ("bob", "muis", 25.0, "2025-01-06"),
    ("carol", "monitor", 300.0, "2025-01-20"),
])
BATCH_2 = orders(4, [
    ("alice", "toetsenbord", 80.0, "2025-02-02"),
    ("dave", "laptop", 1150.0, "2025-02-14"),
])
