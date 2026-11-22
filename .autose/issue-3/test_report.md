# Test report: issue #3 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_3.py::test_update_fails_leaves_documents_unmodified_memory_storage |
| AC-2 | tests/test_autose_issue_3.py::test_update_fails_leaves_documents_unmodified_on_type_error |
| AC-3 | tests/test_autose_issue_3.py::test_update_doc_id_fails_leaves_single_document_unmodified |
| AC-4 | tests/test_autose_issue_3.py::test_update_succeeds_normally |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_3.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

In `Table._update_table`, shallow-copied document dictionaries when populating `table` from `raw_table`. This prevents in-place document mutations in memory (such as with `MemoryStorage`) from altering stored data before the update operation completes or if an exception is raised mid-update.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.53s

```