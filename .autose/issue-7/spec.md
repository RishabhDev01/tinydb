# Spec: Prevent Search Result Mutation from Corrupting Query Cache (issue #7)

**Type:** bug
**Summary:** Returning copies of cached query results prevents in-place mutation of returned documents from altering subsequent search results.

## Current behaviour
In `tinydb/table.py:Table.search`, when a query condition is matched in `self._query_cache`, `Table.search` returns `docs[:]` (a shallow list copy of the cached list of `Document` instances). Because the `Document` objects themselves are shared references with the cached instances, mutating a returned document (e.g. `res[0]['name'] = 'new'`) mutates the object held in `_query_cache`, causing subsequent `search()` calls with the same query to return the mutated data even though no database update occurred. Furthermore, in memory storage or cached table reads, shared dictionary references can leak across operations.

## Required behaviour
When querying documents via `Table.search`, mutating the returned document instances or their contents must not alter the results returned by subsequent queries or the contents stored in the database. `Table.search` must return document objects that are independent copies of the cached documents, ensuring that external modifications do not affect cached or stored query results.

## Acceptance criteria
### AC-1: Modifying search result does not affect subsequent search
- **Given** a table containing `{'name': 'alice', 'role': 'admin'}`
- **When** calling `results1 = table.search(where('role') == 'admin')`, mutating `results1[0]['name'] = 'bob'`, and then calling `results2 = table.search(where('role') == 'admin')`
- **Then** `results2[0]['name']` is `'alice'`

### AC-2: Modifying nested structures in search result does not affect subsequent search
- **Given** a table containing `{'name': 'alice', 'details': {'city': 'London'}}`
- **When** calling `results1 = table.search(where('name') == 'alice')`, mutating `results1[0]['details']['city'] = 'Paris'`, and then calling `results2 = table.search(where('name') == 'alice')`
- **Then** `results2[0]['details']['city']` is `'London'`

### AC-3: Uncached and repeated search results preserve Document type and doc_id
- **Given** a table containing `{'name': 'alice'}` with document ID `1`
- **When** calling `results = table.search(where('name') == 'alice')`
- **Then** `results[0]` is an instance of `Document`, `results[0].doc_id` is `1`, and `results[0]` equals `{'name': 'alice'}`

### AC-4: Search with no matches returns empty list
- **Given** a table containing `{'name': 'alice'}`
- **When** calling `results = table.search(where('name') == 'bob')`
- **Then** `results` is `[]`

## Assumptions
- Returning copies of documents from `search()` (deep copy or reconstructing `Document(copy.deepcopy(doc), doc.doc_id)`) satisfies safety against mutating results (rejected: disabling the query cache entirely, because query caching is an intentional optimization feature in TinyDB).

## Out of scope
- Mutating documents returned from direct internal attributes (e.g. `table._query_cache` private access).
- Performance optimizations beyond maintaining isolation between query results and cached data.

## API touched
- `tinydb.table.Table.search` (existing)