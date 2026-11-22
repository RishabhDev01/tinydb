# Design: Add append operation for list fields

## Approach
Add a new helper function `append(field: str, val: Any) -> Callable[[MutableMapping], None]` to `tinydb.operations`. The inner transform function checks if `field` is present in `doc`: if not, it assigns `doc[field] = [val]`; if present, it calls `doc[field].append(val)`. Calling `.append(val)` on a non-list object without an `append` method will naturally raise `AttributeError`, satisfying AC-3. This relies on the invariant that write updates pass a mutable mapping document to the updater/transform function and clear the query cache via `Table._update_table` (ARCHITECTURE.md Invariant 1).

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/operations.py | append (NEW) | Define `append(field: str, val: Any)` returning a transform function that appends `val` to `doc[field]` if `field in doc` (raising `AttributeError` if not a list/appendable) or sets `doc[field] = [val]` if `field not in doc`. |
| tests/test_operations.py | (NEW tests) | Add tests for `append`: appending to existing list, initializing non-existent field, raising `AttributeError` for non-list field, and ensuring existing operations work as expected. |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_operations.py | test_append_existing_list |
| AC-2 | tests/test_operations.py | test_append_nonexistent_field |
| AC-3 | tests/test_operations.py | test_append_non_list_raises_attribute_error |
| AC-4 | tests/test_operations.py | test_existing_operations_unchanged |

## Risks
- If a custom document or field type has an `append` method with a different signature or semantics, calling `.append(val)` could raise `TypeError` instead of `AttributeError`. However, standard Python types (int, str, dict) do not have `.append` and will raise `AttributeError` as specified. Covered by `test_append_non_list_raises_attribute_error`.
- Existing operation tests in `tests/test_operations.py` ensure no regressions to other operations.