# Design: Table pluck method

## Approach
Add a `pluck(self, field: str) -> list[Any]` method to `Table` in `tinydb/table.py`.
The method iterates over documents in the table (via `self` or `self._read_table().values()`) and extracts `doc[field]` for any document where `field in doc`, returning the collected values in a list.
Calls on `TinyDB` automatically delegate to the default table via `TinyDB.__getattr__`, which forwards unknown attribute lookups directly to `self.table(self.default_table_name)`.
This relies on Invariant 2 (`_read_table()` returns the raw storage dict mapping doc IDs to document dicts in insertion order).

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.pluck (NEW) | Add `pluck(self, field: str) -> list[Any]` to extract field values from documents containing `field` in table iteration order |
| tests/test_tables.py | (NEW tests) | Add unit tests verifying `pluck` for AC-1 through AC-5 |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_pluck_all_present |
| AC-2 | tests/test_tables.py | test_pluck_skipping_missing |
| AC-3 | tests/test_tables.py | test_pluck_preserves_none |
| AC-4 | tests/test_tables.py | test_pluck_non_existent_field |
| AC-5 | tests/test_tables.py | test_pluck_custom_table |

## Risks
- Plucking keys with `None` values could accidentally be excluded if truthiness or `get()` with `None` check is used; avoided by using explicit `field in doc` membership checks. Covered by `test_pluck_preserves_none`.
- Document insertion order preservation across Python/dict implementations; covered by standard dict iteration order in Python 3.7+ and verified in `test_pluck_all_present` and `test_pluck_skipping_missing`.