# Spec: Ensure atomic update on error (issue #3)

**Type:** bug
**Summary:** `TinyDB.update` must leave the database unchanged when an operation (e.g., `increment`) raises a `KeyError`, regardless of storage backend.

## Current behaviour
- `tinydb.table.Table.update` applies the transformation to each matching document sequentially.  
- With `MemoryStorage`, if a transformation raises `KeyError` on a later document, earlier documents may already have been modified (partial update).  
- With `JSONStorage`, the whole update is rolled back on error, leaving the database unchanged.

## Required behaviour
- `Table.update` must be atomic: either all matching documents are updated successfully, or none are changed.  
- The method must detect any exception raised by the transformation callable and abort the operation, restoring the original state of the table.  
- This atomicity must be guaranteed for all storage types, including `MemoryStorage` and any future storage implementations.

## Acceptance criteria
### AC-1: No partial update on MemoryStorage
- **Given** a `TinyDB` instance using `MemoryStorage` with three documents `{'count': 1}`, `{'other': 0}`, `{'count': 5}`
- **When** `db.update(increment('count'))` is called
- **Then** a `KeyError` is raised and the table contents remain exactly `[{'count': 1}, {'other': 0}, {'count': 5}]`

### AC-2: No partial update on JSONStorage
- **Given** a `TinyDB` instance using the default `JSONStorage` with the same three documents persisted in a temporary file
- **When** `db.update(increment('count'))` is called
- **Then** a `KeyError` is raised and the file on disk still contains the original three documents unchanged

### AC-3: Successful update when all documents have the field
- **Given** a `TinyDB` instance using `MemoryStorage` with two documents `{'count': 1}` and `{'count': 5}`
- **When** `db.update(increment('count'))` is called
- **Then** the method returns `2` and the table now contains `[{'count': 2}, {'count': 6}]`

### AC-4: No change when no document matches the query
- **Given** a `TinyDB` instance using `MemoryStorage` with a single document `{'count': 3}`
- **When** `db.update(increment('count'), where('missing') == True)` is called
- **Then** the method returns `0` and the table still contains `[{'count': 3}]`

## Assumptions
- The atomicity requirement is implemented by copying the table state before applying updates and restoring it on any exception (rejected: leaving the table partially modified, because the issue explicitly reports inconsistent behavior across storages).  
- `increment` is the only operation that can raise `KeyError` for a missing field; other operations are assumed to behave similarly under the same atomicity rule.

## Out of scope
- Performance optimisations for the rollback mechanism.  
- Changes to the public API of `increment` or other operation helpers.

## API touched
- `tinydb.table.Table.update` (existing)