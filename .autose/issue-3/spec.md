```markdown
# Spec: Atomic update for operations that may raise (issue #3)

**Type:** bug
**Summary:** `Table.update` must be atomic – if a user‑provided update callable (e.g., `increment('count')`) raises an exception for any matching document, the database state must remain unchanged for **all** storages (including `MemoryStorage`).

## Current behaviour
`Table.update` applies the update callable to each matching document sequentially.  
When a callable raises `KeyError` for a document that lacks the targeted field, the exception propagates, but any documents that were updated earlier remain modified. This occurs with `MemoryStorage` (see `tinydb/table.py:update` lines 447‑476). With `JSONStorage` the whole operation is rolled back, so the behaviour is inconsistent.

## Required behaviour
1. `Table.update` must first determine the set of target document IDs that exist **before** any modifications.
2. It must apply the update callable to all those documents in a *transactional* way: if the callable raises an exception for any document, **no** document is modified and the original data is left intact.
3. The method must still return the list of IDs that would have been updated when the operation succeeds.
4. This atomic semantics must be identical for all storage back‑ends (`MemoryStorage`, `JSONStorage`, etc.).

## Acceptance criteria
### AC-1: Successful atomic update
- **Given** a table with documents `{'count': 1}` (doc_id 1) and `{'count': 5}` (doc_id 2)
- **When** `db.update(increment('count'))` is called
- **Then** the returned list is `[1, 2]` and the table contains `{'count': 2}` (doc_id 1) and `{'count': 6}` (doc_id 2)

### AC-2: Update aborts when a document is missing the field (MemoryStorage)
- **Given** a `MemoryStorage` database with documents `{'count': 1}` (doc_id 1), `{'other': 0}` (doc_id 2), `{'count': 5}` (doc_id 3)
- **When** `db.update(increment('count'))` is called
- **Then** a `KeyError` is raised and the table remains exactly as initially inserted (`{'count': 1}`, `{'other': 0}`, `{'count': 5}`)

### AC-3: Update aborts when a document is missing the field (JSONStorage)
- **Given** a `JSONStorage` database with the same three documents as AC‑2
- **When** `db.update(increment('count'))` is called
- **Then** a `KeyError` is raised and the JSON file on disk is unchanged (the three original documents persist)

### AC-4: No side‑effects on unrelated tables
- **Given** two tables `t1` and `t2` in the same database; `t1` contains a document missing the field, `t2` contains only documents with the field
- **When** `t1.update(increment('count'))` raises `KeyError`
- **Then** `t2.all()` returns its original documents unchanged (the failure of `t1.update` does not affect other tables)

## Assumptions
- The update callable is executed *after* the target IDs are collected (rejected: executing the callable while iterating over the table, because that caused the half‑apply bug).
- The atomicity requirement applies only to the *current* `Table.update` call; it does not require a full transaction system across multiple calls (rejected: implementing a multi‑operation transaction manager, which is out of scope for this bug fix).

## Out of scope
- Introducing a new transaction API for grouping multiple operations.
- Changing the public exception type (still `KeyError` for missing fields).

## API touched
- `tinydb.table.Table.update` (existing)
```