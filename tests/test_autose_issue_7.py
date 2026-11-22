import pytest
from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def test_search_mutation_does_not_affect_subsequent_search():
    """AC-1: Modifying search result does not affect subsequent search."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    table.insert({'name': 'alice', 'role': 'admin'})

    results1 = table.search(where('role') == 'admin')
    results1[0]['name'] = 'bob'

    results2 = table.search(where('role') == 'admin')
    assert results2[0]['name'] == 'alice'


def test_search_nested_mutation_does_not_affect_subsequent_search():
    """AC-2: Modifying nested structures in search result does not affect subsequent search."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    table.insert({'name': 'alice', 'details': {'city': 'London'}})

    results1 = table.search(where('name') == 'alice')
    results1[0]['details']['city'] = 'Paris'

    results2 = table.search(where('name') == 'alice')
    assert results2[0]['details']['city'] == 'London'


def test_search_preserves_document_type_and_doc_id():
    """AC-3: Uncached and repeated search results preserve Document type and doc_id."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'alice'})
    assert doc_id == 1

    # First search (uncached)
    results = table.search(where('name') == 'alice')
    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].doc_id == 1
    assert results[0] == {'name': 'alice'}

    # Second search (cached)
    results_cached = table.search(where('name') == 'alice')
    assert len(results_cached) == 1
    assert isinstance(results_cached[0], Document)
    assert results_cached[0].doc_id == 1
    assert results_cached[0] == {'name': 'alice'}


def test_search_with_no_matches():
    """AC-4: Search with no matches returns empty list."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    table.insert({'name': 'alice'})

    results = table.search(where('name') == 'bob')
    assert results == []
