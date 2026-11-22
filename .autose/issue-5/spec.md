# Spec: Table pluck method (issue #5)

**Type:** feature
**Summary:** Add a `pluck` method to `Table` (and accessible via `TinyDB`) to extract values of a specified field across documents in insertion order, skipping documents missing that field.

## Current behaviour
Not supported. Users extract values by iterating over `db.all()` and accessing the key, which raises `KeyError` if any document lacks the field or requires manual `dict.get` calls and `None` filtering.

## Required behaviour
A new method `pluck(field)` on `Table` (and callable on `TinyDB` via default table forwarding) returns a `list` of values corresponding to `field` for every document containing `field` in the table. Documents that do not contain `field` are skipped. Values are returned in document insertion order (the iteration order of the table).

## Acceptance criteria
### AC-1: Pluck field from documents with all fields present
- **Given** a database where the default table contains documents `{'name': 'alice'}` and `{'name': 'bob'}`
- **When** calling `db.pluck('name')`
- **Then** the return value is `['alice', 'bob']`

### AC-2: Pluck field skipping documents missing the field
- **Given** a database where the default table contains documents `{'name': 'alice', 'age': 30}`, `{'age': 25}`, and `{'name': 'charlie'}`
- **When** calling `db.pluck('name')`
- **Then** the return value is `['alice', 'charlie']`

### AC-3: Pluck preserves None values when key is present
- **Given** a database where the default table contains documents `{'val': None}` and `{'val': 42}`
- **When** calling `db.pluck('val')`
- **Then** the return value is `[None, 42]`

### AC-4: Pluck non-existent field
- **Given** a database where the default table contains documents `{'name': 'alice'}` and `{'name': 'bob'}`
- **When** calling `db.pluck('missing')`
- **Then** the return value is `[]`

### AC-5: Pluck on a custom table
- **Given** a table `db.table('users')` containing documents `{'email': 'alice@example.com'}` and `{'email': 'bob@example.com'}`
- **When** calling `db.table('users').pluck('email')`
- **Then** the return value is `['alice@example.com', 'bob@example.com']`

## Assumptions
- When a document contains the field with value `None`, `None` is included in the output (rejected: filtering out `None` values), because the document possesses the key and only documents missing the key entirely should be skipped.
- `pluck` accepts a single field name as a string (rejected: nested dotted paths or multiple fields), because the issue explicitly requests plucking a single field and keeping the API minimal.

## Out of scope
- Nested path resolution (e.g. `user.address.city`).
- Plucking multiple keys into tuples or sub-dicts.
- Transforming or filtering plucked values via callbacks.

## API touched
- `tinydb.table.Table.pluck` (NEW)