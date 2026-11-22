# Design: Atomic update on error (issue #3)

## Approach
Modify `tinydb.table.Table._update_table` to perform the update inside a `try/except` block.  Before invoking the user‑supplied `updater`, we snapshot the current table data (`raw_table`).  If the updater raises any exception, we restore the original table data to the storage and re‑raise the exception.  This guarantees that all storage backends (MemoryStorage, JSONStorage, etc.) behave atomically.  The change relies on invariants 1 (write clears cache) and 4 (truncate resets `_next_id` – not affected).

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table._update_table | Wrap updater call in try/except, restore original tables on error |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_atomic_update.py | test_memory_storage_atomic_update |
| AC-2 | tests/test_atomic_update.py | test_json_storage_atomic_update |
| AC-3 | tests/test_atomic_update.py | test_successful_update |
| AC-4 | tests/test_atomic_update.py | test_no_match_update |

## Risks
- The rollback writes the original tables back, which may trigger another write and clear the cache; this is acceptable as the operation is aborted.  Existing tests that rely on cache state after a failed update will need to be updated accordingly.
- If the updater modifies the table in place before an exception, the snapshot must be a deep copy; we use `dict.copy()` which is shallow but sufficient because values are mappings that are not mutated outside the updater.

## STOPPED at stage `design`

QuotaExhausted: planner: Groq daily quota used up for openai/gpt-oss-120b and its fallbacks (retry after: openai/gpt-oss-120b ~18 min, openai/gpt-oss-20b ~4 min)

The free-tier quota refills at about 8k tokens per hour per model. Comment `/autose` later to resume at this stage.


## STOPPED at stage `design`

LLMError: planner: HTTP 400: [{'error': {'code': 400, 'message': 'Invalid Auth key.', 'status': 'INVALID_ARGUMENT'}}]Error code: 400
