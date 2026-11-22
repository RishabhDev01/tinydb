# Design: Consistent string doc_ids support across Table methods (issue #4)

## Approach
In `tinydb.table.Table`, doc_ids are stored in memory as integers (`self.document_id_class`). To support string document IDs convertible to int (e.g. `'1'`) consistently across `get`, `remove`, and `update` without breaking non-integer edge cases like `float('NaN')`:
1. In `Table.get`: when `doc_id is not None`, safely attempt `self.document_id_class(doc_id)` (catching `(ValueError, TypeError)`) before looking up in `table`. When found, return `self.document_class(raw_doc, self.document_id_class(doc_id))`. When `doc_ids is not None`, convert each id using `self.document_id_class(d)` (handling/skipping invalid conversions cleanly) so matching integers are looked up.
2. In `Table.remove`: when `doc_ids is not None`, convert `requested_ids` by mapping elements convertible via `self.document_id_class` to `int` (ignoring or gracefully handling values that cannot be converted to `int`, which cannot exist in `table` anyway).
3. In `Table.update`: when `doc_ids is not None`, convert `doc_ids` to `[self.document_id_class(i) for i in doc_ids if ...]` (coercing convertible string IDs to int).

We address earlier test failures where modifying internal keys or improperly handling non-int conversions caused `test_get_ids[memory]` (`float('NaN')`), `test_get_multiple_ids`, etc. to fail: we do NOT touch `_read_table()` or internal storage invariants (Invariant 2: doc IDs in memory are ints); we strictly coerce input arguments at the method boundary in `get`, `update`, and `remove`.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.get | Coerce `doc_id` and elements in `doc_ids` using `self.document_id_class` when possible (catching `ValueError`/`TypeError`), and instantiate `Document` with `self.document_id_class(doc_id)`. |
| tinydb/table.py | Table.remove | Coerce convertible elements of `doc_ids` using `self.document_id_class` before looking up in `table`. |
| tinydb/table.py | Table.update | Coerce convertible elements of `doc_ids` using `self.document_id_class` before looking up in `table`. |
| tests/test_tables.py | (NEW tests) | Add tests for AC-1 through AC-5 covering string doc_ids in remove, update, and get. |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_remove_string_doc_ids |
| AC-2 | tests/test_tables.py | test_update_string_doc_ids |
| AC-3 | tests/test_tables.py | test_get_string_doc_id_returns_int_doc_id |
| AC-4 | tests/test_tables.py | test_remove_int_doc_ids |
| AC-5 | tests/test_tables.py | test_remove_nonexistent_string_doc_id |

## Risks
- Passing unconvertible values (such as `float('NaN')`) to `doc_id` could raise `ValueError` if not caught. Caught with `try...except (ValueError, TypeError)` so non-convertible IDs safely yield `None` or empty results, preserving existing behavior tested in `test_get_ids`.
- Invariant 1 (cache clearing) and Invariant 2 (doc IDs are int in memory) are preserved because we perform argument normalization at the boundary without changing internal table dict keys or storage logic.