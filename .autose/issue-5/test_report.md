# Test report: issue #5 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_5.py::test_pluck_all_matching |
| AC-2 | tests/test_autose_issue_5.py::test_pluck_skipping_missing |
| AC-3 | tests/test_autose_issue_5.py::test_pluck_with_none_value |
| AC-4 | tests/test_autose_issue_5.py::test_pluck_empty_or_nonexistent_field |
| AC-5 | tests/test_autose_issue_5.py::test_pluck_on_custom_table |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | no | BUILD FAILED (stage 3 check): |
| 2 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_5.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Changed the return type annotation in `Table.pluck` from `list[Any]` to `list` because `Any` was not imported in `tinydb/table.py`. This fixes the `NameError: name 'Any' is not defined` import error while maintaining identical functionality.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.43s

```