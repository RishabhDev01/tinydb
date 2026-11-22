# Spec: Pluck field values from table documents (issue #5)

**Type:** feature
**Summary:** Add a `pluck` method to tables to extract a list of values for a specified field across all documents, skipping documents where the field is absent.

## Current behaviour
TinyDB has no `pluck` method on `Table` or `TinyDB` (`Table.pluck` is not supported). Users must retrieve all documents (e.g., via `Table.all()`) and manually extract or filter the desired key.

## Required behaviour
A new method `pluck(key: str) -> list[Any]` is added to `Table`. It returns a list of values associated with `key` for all documents in the table in insertion order. Any document that does not contain `key` is skipped and omitted from the returned list. Because `TinyDB.__getattr__` forwards unknown attributes to the default table, `db.pluck(key)` is also supported.

## Acceptance criteria
### AC-1: Pluck field from documents with all matching keys
- **Given** a table with documents `{'name': 'Alice', 'age': 30}` and `{'name': 'Bob', 'age': 25}` inserted in that order
- **When** calling `table.pluck('name')`
- **Then** the return value is `['Alice', 'Bob']`

### AC-2: Skip documents lacking the plucked field
- **Given** a table with documents `{'name': 'Alice', 'score': 100}`, `{'score': 85}`, and `{'name': 'Charlie', 'score': 90}` inserted in that order
- **When** calling `table.pluck('name')`
- **Then** the return value is `['Alice', 'Charlie']`

### AC-3: Pluck when field value is None vs absent
- **Given** a table with documents `{'name': 'Alice', 'alias': None}` and `{'name': 'Bob'}` inserted in that order
- **When** calling `table.pluck('alias')`
- **Then** the return value is `[None]`

### AC-4: Pluck from an empty table
- **Given** an empty table
- **When** calling `table.pluck('name')`
- **Then** the return value is `[]`

### AC-5: Pluck via default table on TinyDB instance
- **Given** a TinyDB instance `db` with default table containing documents `{'city': 'Paris'}` and `{'city': 'London'}` inserted in that order
- **When** calling `db.pluck('city')`
- **Then** the return value is `['Paris', 'London']`

## Assumptions
- Documents with `key: None` are retained in the result (rejected: treating `None` as missing), because `None` is a valid stored value and only keys absent from the document should be skipped.
- `key` is treated as a top-level document key (rejected: dot-separated nested path resolution), because TinyDB standard dictionary access and issue request specify a single field name.

## Out of scope
- Nested key traversal or path expressions (e.g. `'user.profile.name'`).
- In-place mutation or transformation of plucked values.

## API touched
- `tinydb.table.Table.pluck` (NEW)