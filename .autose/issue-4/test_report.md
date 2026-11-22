# Test report: issue #4 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_4.py::test_remove_string_doc_ids |
| AC-2 | tests/test_autose_issue_4.py::test_update_string_doc_ids |
| AC-3 | tests/test_autose_issue_4.py::test_get_string_doc_id_returns_int_id |
| AC-4 | tests/test_autose_issue_4.py::test_remove_mixed_int_and_string_doc_ids |
| AC-5 | tests/test_autose_issue_4.py::test_remove_unconvertible_string_doc_ids |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | no | TESTS FAILED (stage 4 check): 1 failed, 231 passed, 1 skipped. Each failing test, where it failed and its first error lines: |
| 2 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_4.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Deduplicated converted IDs in `requested_ids` for both `Table.remove` and `Table.update` so that providing equivalent IDs (e.g., `[1, '1']`) does not duplicate the target in `removed_ids`/`updated_ids` or cause a `KeyError` when deleting from the table dict. Document IDs passed to `get`, `remove`, and `update` now consistently map to integer IDs without errors.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.35s

```