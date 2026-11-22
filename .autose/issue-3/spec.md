# Spec: update() with increment() half-applies when one document is missing the field

**Type:** bug
**Summary:** Ensure that a failed update operation leaves the database unchanged, regardless of storage type.

## Current behaviour
When calling `Table.update` with a callable that raises a `KeyError` (e.g., `increment('count')` on a document missing the field), the operation partially applies: documents processed before the error are updated, while the error propagates. In `MemoryStorage` this results in a half‑applied update; in file storage the update is rolled back.

## Required behaviour
All update operations must be atomic: either all matching documents are updated, or none are. If any document causes an exception during the update, the entire operation should abort and the database should remain in its original state.

## Acceptance criteria
### AC-1: Successful update
- **Given** a table with `{'count': 1}` and `{'count': 5}`
- **When** `db.update(increment('count'))`
- **Then** the table contains `{'count': 2}` and `{'count': 6}`

### AC-2: Update fails due to missing field
- **Given** a table with `{'count': 1}`, `{'other': 0}`, and `{'count': 5}`
- **When** `db.update(increment('count'))`
- **Then** a `KeyError` is raised and the table remains unchanged

### AC-3: Update with doc_ids that include a missing field
- **Given** a table with `{'count': 1}`, `{'other': 0}`, and `{'count': 5}`
- **When** `db.update(increment('count'), doc_ids=[1, 2, 3])`
- **Then** a `KeyError` is raised and the table remains unchanged

## Assumptions
- The update operation should be atomic across all documents, not just those processed before the error. (rejected: partial application)
- The exception type raised by `increment` when a field is missing is `KeyError`. (rejected: generic Exception)

## Out of scope
- Changing the semantics of `increment` to provide a default value.
- Modifying the storage layer to support transactional writes.

## API touched
- `tinydb.table.Table.update` (existing)