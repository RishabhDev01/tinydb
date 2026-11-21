# Design: Atomic update for Table.update

## Approach
We will rewrite `Table.update` (in `tinydb/table.py`) to enforce true atomicity. The method will first collect the IDs of all matching documents and retrieve deep‑copies of those documents. It will then apply the user‑provided update callable to each copy, catching any exception. If any callable raises, the original documents remain untouched and the exception is re‑raised, satisfying AC‑2 and AC‑3. Only when all updates succeed will we write the modified documents back via the existing `_update_table` helper, which also clears the query cache (Invariant 1). This change respects Invariant 2 (ID conversion) because we continue to use the internal integer IDs and only interact with storage through `_update_table`. No other tables are touched, preserving AC‑4. The modification is confined to a single method, the smallest change that satisfies all acceptance criteria.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.update | Refactor to (1) collect matching IDs, (2) copy documents, (3) apply update callable on copies inside a try block, (4) on success call `_update_table` with the updated docs, (5) on failure raise the original exception without calling `_update_table`. |
| tests/test_tables.py | (NEW tests) | Add tests for AC‑1, AC‑2, AC‑3, and AC‑4 using both `MemoryStorage` and `JSONStorage`. |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_atomic_update_success_returns_ids_and_modifies_all |
| AC-2 | tests/test_tables.py | test_atomic_update_memory_storage_raises_and_no_change |
| AC-3 | tests/test_tables.py | test_atomic_update_json_storage_raises_and_file_unchanged |
| AC-4 | tests/test_tables.py | test_atomic_update_failure_does_not_affect_other_table |

## Risks
- Changing `Table.update` may affect code that relied on the previous in‑place mutation order. Existing tests that only check the return value of `update` should still pass because we still return the list of updated IDs.
- If any internal helper assumes documents are mutated before `_update_table` is called, it could break. However, `_update_table` only expects the final document mapping, so using copies is safe. Existing tests for other table operations (e.g., `remove`, `upsert`) remain unaffected because they do not depend on `update`’s internal mutation strategy.