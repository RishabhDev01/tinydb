# Spec: Add `append` operation to `tinydb.operations` (issue #6)

**Type:** feature
**Summary:** Provide an `append(field, val)` operation function in `tinydb.operations` to append a value to a list field or initialise a single-item list if the field does not exist.

## Current behaviour
Not supported. `tinydb.operations` only exposes `delete`, `add`, `subtract`, `set`, `increment`, and `decrement`. Users must write a custom updater function to append elements to a list field.

## Required behaviour
A new function `append(field: str, val: Any) -> Callable[[MutableMapping], None]` is added to `tinydb.operations`. When passed to `db.update(...)`, it modifies the targeted document: if `field` is already present in the document, `val` is appended to that field (via `doc[field].append(val)`); if `field` is not present, `doc[field]` is initialized to `[val]`. If `field` exists but is not a list (or does not support `.append`), calling the returned updater on the document raises `AttributeError`.

## Acceptance criteria
### AC-1: Append to existing list field
- **Given** a database with one document `{'id': 1, 'tags': ['urgent']}`
- **When** calling `db.update(append('tags', 'review'), where('id') == 1)`
- **Then** `db.get(where('id') == 1)` returns `{'tags': ['urgent', 'review'], 'id': 1}`

### AC-2: Append when field does not exist
- **Given** a database with one document `{'id': 2}`
- **When** calling `db.update(append('tags', 'urgent'), where('id') == 2)`
- **Then** `db.get(where('id') == 2)` returns `{'tags': ['urgent'], 'id': 2}`

### AC-3: Append to non-list existing field raises AttributeError
- **Given** a database with one document `{'id': 3, 'tags': 42}`
- **When** calling `db.update(append('tags', 'urgent'), where('id') == 3)`
- **Then** an `AttributeError` exception is raised

### AC-4: Existing update operations unchanged
- **Given** a database with one document `{'id': 4, 'count': 1}`
- **When** calling `db.update(increment('count'), where('id') == 4)`
- **Then** `db.get(where('id') == 4)` returns `{'id': 4, 'count': 2}`

## Assumptions
- When the target `field` does not exist in the document, `doc[field]` is set to `[val]` (rejected: raising `KeyError`), because the issue explicitly requested initializing a new list with that one value.
- If `field` exists but is not a list (or lacks `.append()`), `AttributeError` is raised (rejected: coercing non-list values or overwriting them with `[val]`), because silently replacing or coercing user data leads to unintended data loss.

## Out of scope
- List prepend or insertion at an arbitrary index.
- List removal / pop operations.
- Nested dictionary path traversal for `append` (operations in `tinydb.operations` operate on top-level mapping keys).

## API touched
- `tinydb.operations.append` (NEW)