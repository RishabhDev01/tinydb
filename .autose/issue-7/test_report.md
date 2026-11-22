# Test report: issue #7 (round 1)

**Baseline on master:** 227 passed
**Result:** {'failed': 1, 'passed': 230, 'skipped': 1} (exit 1)
**Build (compileall + import):** pass

## Acceptance criteria → tests

| AC | Tests |
|---|---|

## Attempts

| # | Pass | Check message |
|---|---|---|
| 1 | no | TESTS FAILED (stage 4 check): 1 failed, 230 passed, 1 skipped. Each failing test, where it failed and its first error lines: |
| 2 | no | YOUR ANSWER COULD NOT BE APPLIED: no '### REPLACE <path> <name>' or '### ADD <path> <Class/MODULE>' block found. Answer again in exactly the required  |
| 3 | no | TESTS FAILED (stage 4 check): 1 failed, 230 passed, 1 skipped. Each failing test, where it failed and its first error lines: |

## Files changed

- `tests/test_autose_issue_7.py`
- `tinydb/table.py`

## Builder's summary (unverified claim)

Updated `Table.search` to return deep copies of `Document` instances on both cache hits and fresh queries. This ensures mutations to returned search documents (or their nested structures) do not mutate the query cache or affect subsequent searches.

## pytest output (tail)

```
........................................................................ [ 31%]
s....................................................................... [ 62%]
................................................................F....... [ 93%]
................                                                         [100%]
=================================== FAILURES ===================================
_______________ test_query_cache_documents_are_shared_with_cache _______________
tests/test_tinydb.py:753: in test_query_cache_documents_are_shared_with_cache
    assert results3[0]['tags'] == ['a', 'b', 'c']
E   AssertionError: assert ['a', 'b'] == ['a', 'b', 'c']
E     
E     Right contains one more item: 'c'
E     
E     Full diff: (-: missing in left side, +: extra in left side)
E       [
E           'a',
E           'b',
E     -     'c',
E       ]
=========================== short test summary info ============================
FAILED tests/test_tinydb.py::test_query_cache_documents_are_shared_with_cache - AssertionError: assert ['a', 'b'] == ['a', 'b', 'c']
  
  Right contains one more item: 'c'
  
  Full diff: (-: missing in left side, +: extra in left side)
    [
        'a',
        'b',
  -     'c',
    ]
1 failed, 230 passed, 1 skipped in 0.45s

```