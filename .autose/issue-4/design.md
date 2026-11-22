# Design: Consistent string doc_ids support across Table methods

## Approach
In `Table.get`, when `doc_id` is supplied, wrap the returned document ID using `self.document_id_class(doc_id)` instead of passing raw `doc_id` to `self.document_class(raw_doc, ...)`, and safely convert string IDs in `get(doc_ids=...)` so they match the storage string keys. In `Table.remove` and `Table.update`, convert any `doc_ids` passed into an iterable/set of `self.document_id_class` integers before running `_update_table` (safely ignoring any unconvertible values), so that internal updater key matching (`doc_id in doc_ids`) matches integer keys correctly. This adheres to ARCHITECTURE.md Invariant 2 (doc IDs are str in storage, int in memory, and converted at boundaries).

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.get | Wrap document ID with `self.document_id_class(doc_id)` in `doc_id` branch; handle convertible string IDs |
| tinydb/table.py | Table.remove | Coerce provided `doc_ids` to `self.document_id_class` integers so updater matches int keys in table |
| tinydb/table.py | Table.update | Coerce provided `doc_ids` to `self.document_id_class` integers so updater matches int keys in table |
| tests/test_tinydb.py | (NEW tests) | Add tests for string doc_ids in remove, update, and get (AC-1 through AC-5) |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tinydb.py | test_remove_string_doc_ids |
| AC-2 | tests/test_tinydb.py | test_update_string_doc_ids |
| AC-3 | tests/test_tinydb.py | test_get_string_doc_id_returns_int_id |
| AC-4 | tests/test_tinydb.py | test_remove_int_doc_ids_unchanged |
| AC-5 | tests/test_tinydb.py | test_remove_nonexistent_string_doc_ids |

## Risks
- Non-convertible doc_ids (such as `float('nan')` or unparseable strings) could raise `ValueError`/`TypeError` if converted naively without handling; covered by existing `test_get_ids` and careful conversion handling (filtering/ignoring values that fail `document_id_class` conversion).