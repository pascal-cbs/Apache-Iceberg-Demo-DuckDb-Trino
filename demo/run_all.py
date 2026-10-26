"""Draait alle demo's na elkaar."""
from demo import (ex01_basics, ex02_time_travel, ex03_schema_evolution, ex04_partitioning,
                  ex05_row_level, ex06_metadata_maintenance, ex07_branches)

for ex in (ex01_basics, ex02_time_travel, ex03_schema_evolution, ex04_partitioning,
           ex05_row_level, ex06_metadata_maintenance, ex07_branches):
    ex.main()
