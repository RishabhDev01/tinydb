# Design: Add append operation to tinydb.operations

## Approach
Add a new helper function `append(field: str, val: Any) -> Callable[[MutableMapping], None]` to `tinydb.operations`. The returned `transform(doc)` function checks if `field` is in `doc`; if present, it calls `doc[field].append(val)`, which raises `AttributeError` if the value does not have an `append` method (such as an int or non-list); if not present, it sets `doc[field] = [val]`. This change relies on Invariant 1 (writes through `Table.update` with an operation clear the query cache via `_update_table`) and Invariant 2 (updater receives in-memory document dict). Existing update operations remain untouched.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/operations.py | append (NEW) | Implement `append(field: str, val: Any) -> Callable[[MutableMapping], None]` returning a transform function that appends `val` to `doc[field]` or initializes `doc[field] = [val]` |
| tests/test_operations.py | (NEW tests) | Add tests `test_append_existing_list`, `test_append_nonexistent_field`, `test_append_non_list_raises`, and `test_existing_operations_unchanged` covering AC-1 through AC-4 |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_operations.py | test_append_existing_list |
| AC-2 | tests/test_operations.py | test_append_nonexistent_field |
| AC-3 | tests/test_operations.py | test_append_non_list_raises |
| AC-4 | tests/test_operations.py | test_existing_operations_unchanged |

## Risks
- Direct lookup `field in doc` vs accessing `doc[field]`: `MutableMapping` supports `in` check and `__getitem__`/`__setitem__`. Handled by checking `if field in doc: doc[field].append(val) else: doc[field] = [val]`. Covered by all test cases in `tests/test_operations.py`.
- If `doc[field]` is not a list, calling `.append(val)` directly raises `AttributeError` naturally. Covered by `test_append_non_list_raises`.