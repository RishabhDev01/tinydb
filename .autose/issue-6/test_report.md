# Test report: issue #6 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_6.py::test_append_existing_list |
| AC-2 | tests/test_autose_issue_6.py::test_append_field_not_exists |
| AC-3 | tests/test_autose_issue_6.py::test_append_non_list_raises_attribute_error |
| AC-4 | tests/test_autose_issue_6.py::test_existing_update_operations_unchanged |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_6.py`
- `tinydb/operations.py`

## Builder's summary (unverified claim)

Added the `append` operation to `tinydb.operations`. It appends a value to an existing list field or initializes the field as a single-element list if it does not exist, raising an `AttributeError` if the existing field value lacks an `append` method.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.68s

```