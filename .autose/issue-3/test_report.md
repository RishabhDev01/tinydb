# Test report: issue #3 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 231, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_3.py::test_update_failure_leaves_documents_unmodified_memory_storage |
| AC-2 | tests/test_autose_issue_3.py::test_update_failure_with_custom_callable_leaves_documents_unmodified |
| AC-3 | tests/test_autose_issue_3.py::test_update_failure_with_doc_ids_leaves_documents_unmodified |
| AC-4 | tests/test_autose_issue_3.py::test_successful_update_persists_changes |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_3.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

In `Table._update_table`, when constructing the in-memory document mapping `table`, we now copy each document (`doc.copy()`) instead of referencing the original dictionary directly. This ensures that in-memory storages like `MemoryStorage` are not mutated in place if an updater raises an exception partway through the operation, making updates atomic across all storage backends.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
231 passed, 1 skipped in 0.71s

```