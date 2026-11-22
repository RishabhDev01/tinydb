import pytest
from tinydb import TinyDB, Query
from tinydb.table import Document
from tinydb.storages import MemoryStorage


def test_ac1_top_level_mutation():
    """AC-1: results2[0]['name'] is 'alice'."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 30})

    User = Query()
    results1 = db.search(User.name == 'alice')
    assert results1[0]['name'] == 'alice'

    results1[0]['name'] = 'bob'

    results2 = db.search(User.name == 'alice')
    assert results2[0]['name'] == 'alice'


def test_ac2_nested_mutation():
    """AC-2: results2[0]['details']['city'] is 'London'."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'details': {'city': 'London'}})

    User = Query()
    results1 = db.search(User.name == 'alice')
    assert results1[0]['details']['city'] == 'London'

    results1[0]['details']['city'] = 'Paris'

    results2 = db.search(User.name == 'alice')
    assert results2[0]['details']['city'] == 'London'


def test_ac3_document_instance_and_metadata():
    """AC-3: results[0] is an instance of Document, results[0].doc_id is 1, and results[0] equals expected dict."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 30})

    User = Query()
    results = db.search(User.name == 'alice')
    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].doc_id == 1
    assert results[0] == {'name': 'alice', 'age': 30}

    # Verify cached query also returns Document instance with doc_id
    cached_results = db.search(User.name == 'alice')
    assert len(cached_results) == 1
    assert isinstance(cached_results[0], Document)
    assert cached_results[0].doc_id == 1
    assert cached_results[0] == {'name': 'alice', 'age': 30}


def test_ac4_empty_results():
    """AC-4: results is []."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 30})

    User = Query()
    results = db.search(User.name == 'nonexistent')
    assert results == []

    # Verify cached search also returns empty list
    cached_results = db.search(User.name == 'nonexistent')
    assert cached_results == []
