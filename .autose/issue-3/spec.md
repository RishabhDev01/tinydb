# Spec: Atomic table updates when an updater raises an exception (issue #3)

**Type:** bug
**Summary:** Failed update operations leave stored documents unmodified regardless of the storage backend.

## Current behaviour
In `tinydb.table.Table._update_table`, `_read_table()` returns the tables dictionary from storage. For `MemoryStorage`, the dictionary returned by `read()` is stored directly in `self.memory`. When `updater(table)` mutates documents in place (e.g. via `tinydb.operations.increment`) and an exception is raised before the update finishes, documents modified prior to the failure remain altered in `MemoryStorage.memory`. In contrast, file-based storages (such as `JSONStorage`) only commit changes on `_storage.write()`, so failed updates leave the stored JSON file untouched.

## Required behaviour
A failed `Table.update` (or any operation using `_update_table`) must be atomic: if an exception is raised while updating documents, no changes from the failed operation are persisted into storage. When an update fails, all documents in the table retain their original values, ensuring consistent behaviour across storage implementations (such as `MemoryStorage` and file-backed storages).

## Acceptance criteria
### AC-1: Update error with MemoryStorage leaves documents unchanged (reproducing case)
- **Given** a `TinyDB` instance with `storage=MemoryStorage` containing documents `{'count': 1}`, `{'other': 0}`, and `{'count': 5}`
- **When** calling `db.update(increment('count'))` and catching the raised `KeyError`
- **Then** `db.all()` equals `[{'count': 1}, {'other': 0}, {'count': 5}]`

### AC-2: Update error with conditional query leaves documents unchanged
- **Given** a `TinyDB` instance with `storage=MemoryStorage` containing documents `{'group': 'a', 'val': 10}` and `{'group': 'a', 'val': 'not_an_int'}`
- **When** calling `db.update(increment('val'), Query().group == 'a')` and catching the raised `TypeError`
- **Then** `db.all()` equals `[{'group': 'a', 'val': 10}, {'group': 'a', 'val': 'not_an_int'}]`

### AC-3: Update error with doc_ids leaves documents unchanged
- **Given** a `TinyDB` instance with `storage=MemoryStorage` containing doc ID 1 with `{'val': 10}` and doc ID 2 with `{'other': 20}`
- **When** calling `db.update(increment('val'), doc_ids=[1, 2])` and catching the raised `KeyError`
- **Then** `db.get(doc_id=1)` equals `{'val': 10}`

### AC-4: Successful update persists modified documents
- **Given** a `TinyDB` instance with `storage=MemoryStorage` containing documents `{'count': 1}` and `{'count': 5}`
- **When** calling `db.update(increment('count'))`
- **Then** `db.all()` equals `[{'count': 2}, {'count': 6}]`

## Assumptions
- Failed table updates should roll back changes in memory / not mutate the stored state on failure (rejected: documenting that `MemoryStorage` is non-transactional), because users expect consistent behavior between `MemoryStorage` and file storages.

## Out of scope
- Making individual user-provided update functions catch their own errors; any unhandled exception in an updater should still be raised to the caller.
- Transaction rollback across multiple separate database calls.

## API touched
- `tinydb.table.Table._update_table` (existing)
- `tinydb.table.Table.update` (existing)