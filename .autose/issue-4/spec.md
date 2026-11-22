# Spec: Consistent string doc_ids support across Table methods (issue #4)

**Type:** bug
**Summary:** Allow string document IDs convertible to int in `remove(doc_ids=...)` and `update(..., doc_ids=...)`, and ensure returned document IDs are integers matching `document_id_class`.

## Current behaviour
In `tinydb.table.Table.get`, when `doc_id` is supplied (e.g. `'1'`), `table.get(str(doc_id))` finds the document stored under key `'1'`, but returns `self.document_class(raw_doc, doc_id)`, which leaves `doc.doc_id` as the original string type instead of `self.document_id_class(doc_id)` (an `int`).

In `tinydb.table.Table.remove` and `tinydb.table.Table.update`, when `doc_ids` are passed, the methods iterate over `doc_ids` and delete or modify keys by integer ID directly (e.g., in `_update_table` via `doc_id in doc_ids`). Since `_read_table()` keys are integers, passing string IDs like `['1']` fails to match any documents, silently returning `[]` without removing or updating anything.

## Required behaviour
When string document IDs convertible to `int` (such as `'1'`) are provided via `doc_ids` to `Table.remove` and `Table.update`, or via `doc_id` to `Table.get`, they are converted using `self.document_id_class` (or treated as integers) so that the operations match and modify the corresponding documents. Furthermore, `Table.get(doc_id=...)` returns a `Document` whose `doc_id` attribute is coerced using `self.document_id_class` (e.g. `int`), ensuring consistent `int` document IDs regardless of whether a string or int was passed.

## Acceptance criteria
### AC-1: Remove documents with string doc_ids
- **Given** a table with one document `{'name': 'a'}` having `doc_id` `1`
- **When** calling `table.remove(doc_ids=['1'])`
- **Then** the call returns `[1]` and `table.all()` returns `[]`

### AC-2: Update documents with string doc_ids
- **Given** a table with one document `{'name': 'a'}` having `doc_id` `1`
- **When** calling `table.update({'name': 'b'}, doc_ids=['1'])`
- **Then** the call returns `[1]` and `table.get(doc_id=1)` returns `Document({'name': 'b'}, doc_id=1)`

### AC-3: Get document with string doc_id returns integer doc_id attribute
- **Given** a table with one document `{'name': 'a'}` having `doc_id` `1`
- **When** calling `table.get(doc_id='1')`
- **Then** the return value is `Document({'name': 'a'}, doc_id=1)` with `doc.doc_id == 1` and `isinstance(doc.doc_id, int)` is `True`

### AC-4: Integer doc_ids behaviour unchanged
- **Given** a table with one document `{'name': 'a'}` having `doc_id` `1`
- **When** calling `table.remove(doc_ids=[1])`
- **Then** the call returns `[1]` and `table.all()` returns `[]`

### AC-5: Non-existent or non-matching string doc_id returns empty result
- **Given** a table with one document `{'name': 'a'}` having `doc_id` `1`
- **When** calling `table.remove(doc_ids=['999'])`
- **Then** the call returns `[]` and `len(table)` returns `1`

## Assumptions
- String IDs convertible to `int` are coerced to integers matching `document_id_class` across ID lookup arguments (rejected: strictly requiring `int` doc_id and raising `TypeError` for string doc_ids, because `get(doc_id=...)` already accepted string IDs and user expects uniform lenient behaviour).

## Out of scope
- Non-integer string IDs (e.g. UUIDs or arbitrary text IDs) when using default `document_id_class = int`.
- Changing the storage format or internal dictionary key representation of `Table`.

## API touched
- `tinydb.table.Table.get` (existing)
- `tinydb.table.Table.remove` (existing)
- `tinydb.table.Table.update` (existing)