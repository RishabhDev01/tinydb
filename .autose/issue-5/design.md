# Design: Pluck field values from table documents

## Approach
Add a `pluck(self, key: str) -> list[Any]` method to `Table` in `tinydb/table.py`.
The method reads all documents in the table (via `self._read_table().values()`, or iterating documents) and collects `doc[key]` for each document where `key in doc`.
Because `_read_table()` returns the raw storage dict maintaining document order, accessing `doc[key]` directly avoids wrapping documents in `Document` instances if iterating `self._read_table().values()`, while also preserving Python dict insertion ordering.
Documents with `doc[key] is None` are preserved because `key in doc` evaluates to `True`, while documents lacking `key` are skipped.
Per ARCHITECTURE.md §5, table methods are automatically forwarded from `TinyDB` via `__getattr__`, so `db.pluck(key)` works without edits to `TinyDB`.
This read operation does not mutate storage and adheres to Invariant 2 (no write / updater conversions needed).

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.pluck (NEW) | Add `pluck(self, key: str) -> list[Any]` method to extract values for `key` across documents, skipping documents where `key not in doc` |
| tests/test_tables.py | (NEW tests) | Add tests for `Table.pluck` and `db.pluck` covering AC-1 through AC-5 |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_pluck_all_matching |
| AC-2 | tests/test_tables.py | test_pluck_missing_key_skipped |
| AC-3 | tests/test_tables.py | test_pluck_none_value_retained |
| AC-4 | tests/test_tables.py | test_pluck_empty_table |
| AC-5 | tests/test_tables.py | test_pluck_db_forwarding |

## Risks
- None identified: `pluck` is a read-only method on `Table` with no side effects on cache or storage. Existing table and query tests in `tests/test_tables.py` and `tests/test_tinydb.py` ensure no regressions.