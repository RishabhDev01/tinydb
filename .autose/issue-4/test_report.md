# Test report: issue #4 (round 1)

**Baseline on master:** 227 passed
**Result:** {'passed': 232, 'skipped': 1} (exit 0)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|
| AC-1 | tests/test_autose_issue_4.py::test_remove_with_str_doc_ids |
| AC-2 | tests/test_autose_issue_4.py::test_update_with_str_doc_ids |
| AC-3 | tests/test_autose_issue_4.py::test_get_with_str_doc_id |
| AC-4 | tests/test_autose_issue_4.py::test_remove_with_int_doc_ids |
| AC-5 | tests/test_autose_issue_4.py::test_remove_with_invalid_str_doc_ids |

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | yes | all checks pass |

## Files changed

- `tests/test_autose_issue_4.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Converted document IDs passed into `Table.remove` and `Table.update` using `self.document_id_class` (silently ignoring invalid ones) so that string document IDs convertible to int match the integer keys in updater tables. Also updated `Table.get` when `doc_id` is passed to instantiate the returned `Document` with `self.document_id_class(doc_id)` to ensure the returned document's `doc_id` is an `int`.

## pytest output (tail)

```
........................................................................ [ 30%]
.s...................................................................... [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
232 passed, 1 skipped in 0.44s

```