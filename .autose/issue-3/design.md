# Design: Atomic table updates when an updater raises an exception

## Approach
In `Table._update_table`, when `raw_table` is retrieved from `tables[self.name]`, mutating documents in `table` (e.g. in-place modifications from `updater(table)`) directly mutates documents in `MemoryStorage.memory` if `MemoryStorage` holds references to the same dictionaries. If an unhandled exception is raised during `updater(table)` (or during doc ID processing), documents updated prior to the exception remain mutated in storage, violating atomicity.
To ensure atomicity across all storage backends without modifying stored documents upon failure, `_update_table` will shallow/deep-copy each document dictionary (via `copy.deepcopy` or `dict(doc)`) when building `table`. Because documents may be nested mappings/data structures modified in place, using `copy.deepcopy(doc)` ensures that in-memory modifications only apply to isolated copies. Only when `updater(table)` succeeds without raising an exception are the updated documents written back to storage via `self._storage.write(tables)`.
This preserves Invariant 1 (every write clears the query cache via `self.clear_cache()` following `_storage.write`), Invariant 2 (doc ID string/int conversions), and requires no changes to `MemoryStorage` or the storage interface.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table._update_table | Deep-copy documents when constructing `table` from `raw_table` so failed updater executions do not mutate stored documents. |
| tests/test_tinydb.py | (NEW tests) | Add test cases for AC-1, AC-2, AC-3, and AC-4 verifying atomic updates with `MemoryStorage`. |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tinydb.py | test_update_error_memory_storage_leaves_documents_unchanged |
| AC-2 | tests/test_tinydb.py | test_update_error_with_conditional_query_leaves_documents_unchanged |
| AC-3 | tests/test_tinydb.py | test_update_error_with_doc_ids_leaves_documents_unchanged |
| AC-4 | tests/test_tinydb.py | test_update_success_memory_storage_persists_changes |

## Risks
- Performance overhead of `copy.deepcopy` during update operations: `copy.deepcopy` is standard for JSON-serializable documents in Python and TinyDB tables are lightweight. Existing test suite covering all update operations in `tests/test_tinydb.py` and `tests/test_tables.py` will verify no regressions.