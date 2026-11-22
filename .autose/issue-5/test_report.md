# Test report: issue #5 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_5.py::test_pluck_all_present |
| AC-2 | tests/test_autose_issue_5.py::test_pluck_skipping_missing |
| AC-3 | tests/test_autose_issue_5.py::test_pluck_preserves_none |
| AC-4 | tests/test_autose_issue_5.py::test_pluck_non_existent |
| AC-5 | tests/test_autose_issue_5.py::test_pluck_custom_table |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | no | BUILD FAILED (stage 3 check): |
| 2 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_5.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Changed the return type annotation of `Table.pluck` from `list[Any]` to `list` because `Any` was not imported in `tinydb/table.py`. This resolves the `NameError` on import while keeping the exact functionality required by all acceptance criteria.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.73s

```