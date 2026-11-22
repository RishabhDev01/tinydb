# Test report: issue #6 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_6.py::test_append_existing_list |
| AC-2 | tests/test_autose_issue_6.py::test_append_nonexistent_field |
| AC-3 | tests/test_autose_issue_6.py::test_append_non_list_field |
| AC-4 | tests/test_autose_issue_6.py::test_append_coexists_with_other_operations |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_6.py`
- `tinydb/operations.py`

## Builder's summary (unverified claim)

Added the `append(field: str, val: Any)` helper operation function in `tinydb/operations.py`. It appends the value if the target field exists on the document (or raises `AttributeError` if the value is not a list-like object with `.append()`), and initializes a new single-element list containing `val` if the field does not exist.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.59s

```