"""03 - Schema-evolutie: kolommen toevoegen, hernoemen, type verbreden, verwijderen - zonder data te herschrijven."""
import pyarrow as pa
from pyiceberg.schema import Schema
from pyiceberg.types import DoubleType, FloatType, LongType, NestedField, StringType

from demo.common import console, fresh_catalog, q, titel, uitleg
from demo.data import BATCH_1, BATCH_2


def main():
    titel("03 - Schema-evolutie")
    schema = Schema(
        NestedField(1, "order_id", LongType(), required=True),
        NestedField(2, "customer", StringType()),
        NestedField(3, "product", StringType()),
        NestedField(4, "amount", FloatType()),  # bewust float32; later verbreden naar double
    )
    tbl = fresh_catalog().create_table("demo.orders", schema=schema)
    tbl.append(BATCH_1.select(["order_id", "customer", "product"]).append_column(
        "amount", BATCH_1["amount"].cast(pa.float32())))

    uitleg("1) Kolom toevoegen - oude rijen krijgen NULL, geen herschrijving van parquet:")
    with tbl.update_schema() as u:
        u.add_column("land", StringType(), doc="ISO-landcode")
    q(tbl, "SELECT order_id, customer, land FROM {t} ORDER BY 1")

    uitleg("2) Kolom hernoemen - oude bestanden blijven werken want Iceberg gebruikt field-ids, geen namen:")
    with tbl.update_schema() as u:
        u.rename_column("product", "artikel")
    q(tbl, "SELECT order_id, artikel FROM {t} ORDER BY 1")

    uitleg("3) Type verbreden (float -> double):")
    with tbl.update_schema() as u:
        u.update_column("amount", field_type=DoubleType())
    console.print("  ", tbl.schema().find_field("amount"))

    uitleg("4) Nieuwe data schrijven met het nieuwe schema; oude en nieuwe rijen staan naast elkaar:")
    nieuw = BATCH_2.select(["order_id", "customer", "product", "amount"]).rename_columns(
        ["order_id", "customer", "artikel", "amount"]).append_column("land", pa.array(["NL", "BE"]))
    tbl.append(nieuw.cast(tbl.schema().as_arrow()))
    q(tbl, "SELECT * FROM {t} ORDER BY order_id")

    uitleg("5) Kolom verwijderen:")
    with tbl.update_schema() as u:
        u.delete_column("land")
    q(tbl, "SELECT * FROM {t} ORDER BY order_id")


if __name__ == "__main__":
    main()
