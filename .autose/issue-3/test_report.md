# Test report: issue #3 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_3.py::test_update_error_leaves_documents_unchanged |
| AC-2 | tests/test_autose_issue_3.py::test_update_error_conditional_query_leaves_documents_unchanged |
| AC-3 | tests/test_autose_issue_3.py::test_update_error_doc_ids_leaves_documents_unchanged |
| AC-4 | tests/test_autose_issue_3.py::test_successful_update_persists_modified_documents |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | no | TESTS FAILED (stage 4 check): 93 failed, 138 passed, 1 skipped. Each failing test, where it failed and its first error lines: |
| 2 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_3.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Imported `copy` inside `Table._update_table` to fix the `NameError: name 'copy' is not defined`. This allows `copy.deepcopy` to isolate documents during table updates so failures leave storage untouched.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.43s

```