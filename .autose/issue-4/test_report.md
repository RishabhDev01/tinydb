# Test report: issue #4 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_4.py::test_ac1_remove_string_doc_ids |
| AC-2 | tests/test_autose_issue_4.py::test_ac2_update_string_doc_ids |
| AC-3 | tests/test_autose_issue_4.py::test_ac3_get_string_doc_id |
| AC-4 | tests/test_autose_issue_4.py::test_ac4_integer_doc_ids_unchanged |
| AC-5 | tests/test_autose_issue_4.py::test_ac5_non_existent_string_doc_id |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_4.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

In `Table.get`, converted `doc_id` via `self.document_id_class(doc_id)` when instantiating the returned `Document` so string doc IDs yield integer `doc_id` attributes. In `Table.remove` and `Table.update`, converted `doc_ids` elements to `self.document_id_class` (silently skipping unconvertible IDs) so string IDs correctly match the table's integer doc IDs in the updater callbacks. Added unit tests for each acceptance criterion in `tests/test_autose_issue_4.py`.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.44s

```