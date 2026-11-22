# Design: Add append operation for list fields

## Approach
Add a new update operation `append(field: str, val: Any) -> Callable[[MutableMapping], None]` to `tinydb.operations`.
Inside the returned `transform(doc)` function:
- If `field` is not in `doc`: initialize `doc[field] = [val]`.
- Else: call `doc[field].append(val)`. If `doc[field]` is not a list (or does not implement `.append`), this naturally raises `AttributeError` without needing extra type assertions.
This is the smallest correct change because it only touches `tinydb/operations.py` where other operations live. It relies on the ARCHITECTURE.md invariant that `Table.update` handles clearing query caches via `_update_table`, so transform functions merely mutate the mutable mapping passed to them.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/operations.py | append (NEW) | Define `append(field: str, val: Any) -> Callable[[MutableMapping], None]` to append `val` to `doc[field]` if present, or set `doc[field] = [val]` if absent |
| tests/test_operations.py | (NEW tests) | Add tests for `append` covering AC-1, AC-2, AC-3, and AC-4 |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_operations.py | test_append_existing_list |
| AC-2 | tests/test_operations.py | test_append_new_field |
| AC-3 | tests/test_operations.py | test_append_non_list_raises_attribute_error |
| AC-4 | tests/test_operations.py | test_existing_operations_unchanged |

## Risks
- Target field object has an `.append` method that behaves differently from list (e.g. custom objects). Handled naturally as specified by the Pythonic `doc[field].append(val)` duck typing. Existing tests in `tests/test_operations.py` cover existing operations.