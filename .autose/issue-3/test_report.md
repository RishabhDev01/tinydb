# Test report: issue #3 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_3.py::test_update_error_memory_storage_leaves_documents_unchanged |
| AC-2 | tests/test_autose_issue_3.py::test_update_error_conditional_query_leaves_documents_unchanged |
| AC-3 | tests/test_autose_issue_3.py::test_update_error_with_doc_ids_leaves_documents_unchanged |
| AC-4 | tests/test_autose_issue_3.py::test_successful_update_persists_modified_documents |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_3.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

In `Table._update_table`, documents from `raw_table` are now copied via `copy.deepcopy(doc)` when building the in-memory `table` dictionary. This prevents in-place mutations (e.g. from `increment` or updater functions) from modifying `MemoryStorage` documents directly before an unhandled exception occurs, ensuring update atomicity.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.59s

```