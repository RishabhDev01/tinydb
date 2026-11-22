# Test report: issue #4 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_4.py::test_ac1_remove_string_doc_ids |
| AC-2 | tests/test_autose_issue_4.py::test_ac2_update_string_doc_ids |
| AC-3 | tests/test_autose_issue_4.py::test_ac3_get_string_doc_id_returns_integer_attribute |
| AC-4 | tests/test_autose_issue_4.py::test_ac4_integer_doc_ids_unchanged |
| AC-5 | tests/test_autose_issue_4.py::test_ac5_non_existent_or_non_matching_string_doc_id |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_4.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

In `Table.get`, ensured that when `doc_id` is passed, the returned `Document` wraps the ID as `self.document_id_class(doc_id)` so string IDs return an integer `doc_id` attribute. In `Table.remove` and `Table.update`, converted requested `doc_ids` to `self.document_id_class` integers (skipping unconvertible IDs) so they match in-memory integer IDs during `updater(table)`.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.46s

```