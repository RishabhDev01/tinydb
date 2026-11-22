# Spec: Add `append` operation for list fields (issue #6)

**Type:** feature
**Summary:** Add an `append` operation to `tinydb.operations` that appends a value to an existing list field or initializes a new single-element list if the field does not exist.

## Current behaviour
`tinydb.operations` provides `delete`, `add`, `subtract`, `set`, `increment`, and `decrement`, but no operation for appending elements to list fields. Users must write custom transform functions to append elements to lists in documents.

## Required behaviour
`tinydb.operations` exports a new function `append(field: str, val: Any) -> Callable[[MutableMapping], None]`. When called on a document, if the target field exists and is a list, `val` is appended to that list; if the target field does not exist in the document, it is created with `[val]`. If the field exists but is not a list (e.g. integer, string, dict), calling the transform function raises `AttributeError`.

## Acceptance criteria
### AC-1: Append to existing list field
- **Given** a database containing `{'id': 1, 'tags': ['urgent']}`
- **When** `db.update(append('tags', 'review'), where('id') == 1)` is called
- **Then** `db.get(where('id') == 1)` returns `{'id': 1, 'tags': ['urgent', 'review']}`

### AC-2: Append to non-existent field initializes list
- **Given** a database containing `{'id': 2}`
- **When** `db.update(append('tags', 'urgent'), where('id') == 2)` is called
- **Then** `db.get(where('id') == 2)` returns `{'id': 2, 'tags': ['urgent']}`

### AC-3: Append to field with non-list value raises AttributeError
- **Given** a database containing `{'id': 3, 'tags': 'urgent'}`
- **When** `db.update(append('tags', 'review'), where('id') == 3)` is called
- **Then** `AttributeError` is raised

### AC-4: Existing operations remain unchanged
- **Given** a database containing `{'id': 4, 'count': 1}`
- **When** `db.update(increment('count'), where('id') == 4)` is called
- **Then** `db.get(where('id') == 4)` returns `{'id': 4, 'count': 2}`

## Assumptions
- When the target field does not exist in the document, initializing it as `[val]` (rejected: raising `KeyError`), because the issue explicitly requested: "If the document doesn't have the field yet, it should start a new list with that one value".
- When the target field exists but is not a list, calling `.append(val)` on it raises `AttributeError` (rejected: converting non-list values into lists or ignoring them), because standard Python types without an `append` method naturally raise `AttributeError`, matching `doc[field].append(val)` semantics in Python.

## Out of scope
- `extend`, `insert`, `remove`, or other list operations.
- Appending multiple elements at once (e.g., `*args`).
- Modifying nested fields or path-based access.

## API touched
- `tinydb.operations.append` (NEW)