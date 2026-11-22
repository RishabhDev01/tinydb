# Design: Prevent Search Result Mutation from Corrupting Query Cache

## Approach
Currently, `Table.search` returns `cached_results[:]` on cache hits and cached instances on fresh queries. Because `Document` objects stored in `_query_cache` are shared references, mutating a returned document (top-level or nested values) corrupts subsequent search results served from the cache.
To fix this, `Table.search` will return independent copies of the matching `Document` objects using `copy.deepcopy(doc)` (or `self.document_class(copy.deepcopy(doc), doc.doc_id)`). This guarantees that external mutations to returned document dictionaries or nested structures do not alter the cached objects or subsequent query results, satisfying AC-1 through AC-4.
Addressing the previous failure: the existing test `test_query_cache_documents_are_shared_with_cache` in `tests/test_tinydb.py` specifically asserted the old, bug-tolerant behavior where mutating `results2[0]['tags']` mutated the cached document so that `results3[0]['tags'] == ['a', 'b', 'c']`. Under this issue spec (#7), that behavior is explicitly identified as the bug to fix. We update `test_query_cache_documents_are_shared_with_cache` in `tests/test_tinydb.py` to assert that mutating documents does *not* corrupt subsequent search results, and add tests covering nested mutations, doc ID preservation, and empty match results.

## Files to change
| File | Function / class | Change |
|---|---|---|
| tinydb/table.py | Table.search | Deep-copy documents before returning from `search()`, returning independent `Document` instances both from cache hits and fresh evaluations |
| tests/test_tinydb.py | test_query_cache_documents_are_shared_with_cache | Update assertions to verify that mutating returned documents does not corrupt subsequent search results |
| tests/test_tables.py | (NEW tests) | Add test cases for AC-1, AC-2, AC-3, AC-4 covering search result mutation isolation, nested mutation, doc_id preservation, and empty queries |

## Test plan
| AC | Test file | Test name |
|---|---|---|
| AC-1 | tests/test_tables.py | test_search_result_mutation_does_not_affect_subsequent_search |
| AC-2 | tests/test_tables.py | test_search_result_nested_mutation_does_not_affect_subsequent_search |
| AC-3 | tests/test_tables.py | test_search_result_preserves_document_type_and_doc_id |
| AC-4 | tests/test_tables.py | test_search_no_matches_returns_empty_list |

## Risks
- Existing test `test_query_cache_documents_are_shared_with_cache` in `tests/test_tinydb.py` expects shared mutable documents between cache and caller; updating this test to reflect the new behavior aligns it with the spec requirements.
- Performance overhead of `copy.deepcopy` on returned documents: mitigated because queries return matched documents rather than entire tables, and correctness/isolation of query cache takes priority.