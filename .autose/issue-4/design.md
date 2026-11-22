# Design: Consistent string doc_ids support across Table methods

## Approach
In `tinydb.table.Table`, doc IDs in storage are string representations (`'1'`), while `Table.get(doc_id=...)` previously returned `self.document_class(raw_doc, doc_id)`, which kept `doc.doc_id` as whatever was passed in (e.g. `str`) rather than casting with `self.document_id_class(doc_id)`.
In `Table.remove` and `Table.update`, the `doc_ids` parameter is matched against table keys using `str(doc_id)`. Specifically:
- `Table.get`: Return `self.document_class(raw_doc, self.document_id_class(doc_id))` so `doc.doc_id` is always coerced to `self.document_id_class` (e.g. `int`), satisfying AC-3 and Invariant 2.
- `Table.remove`: When `doc_ids` is provided, normalize the lookup set as `doc_ids_set = {str(d) for d in doc_ids}` and collect removed IDs converted using `self.document_id_class(doc_id)`.
- `Table.update`: When `doc_ids` is provided, normalize the lookup set as `doc_ids_set = {str(d) for d in doc_ids}` and collect updated IDs converted using `self.document_id_class(doc_id)`.
This addresses the earlier failure where modifying internal representation or converting types in `_read_table`/`_update_table` broke storage keys (which must remain string keys in storage according to Invariant 2). By leaving internal table keys as strings and coercing input `doc_ids` to strings for table membership matching, and coercing return doc IDs with `self.document_id_class`, all existing tests pass while satisfying AC-1 through AC-5.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.get | Wrap `doc_id` in `self.document_id_class(doc_id)` when constructing `Document(raw_doc, ...)` |
| tinydb/table.py | Table.remove | Coerce items in `doc_ids` to strings (`set(str(d) for d in doc_ids)`) for table lookup |
| tinydb/table.py | Table.update | Coerce items in `doc_ids` to strings (`set(str(d) for d in doc_ids)`) for table lookup |
| tests/test_tables.py | (NEW tests) | Add tests for string doc_id support in remove, update, and get |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_remove_string_doc_ids |
| AC-2 | tests/test_tables.py | test_update_string_doc_ids |
| AC-3 | tests/test_tables.py | test_get_string_doc_id_coerced_int |
| AC-4 | tests/test_tables.py | test_remove_int_doc_ids |
| AC-5 | tests/test_tables.py | test_remove_nonexistent_string_doc_id |

## Risks
- Non-convertible doc IDs could raise `ValueError`/`TypeError` if invalid types are passed, which is consistent with the assumption of string IDs convertible to `int`.
- Invariant 2 (Doc IDs are `str` in storage and `int` in memory) is preserved because storage dictionary keys remain strings and output document IDs are converted using `self.document_id_class`. Existing tests in `test_tinydb.py` and `test_tables.py` verify this.