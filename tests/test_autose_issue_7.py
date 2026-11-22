import pytest
from tinydb import TinyDB, Query
from tinydb.table import Document
from tinydb.storages import MemoryStorage


def test_ac1_mutating_toplevel_field_does_not_affect_cached_search():
    """AC-1: results2[0]['name'] is 'alice'."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    user = Query()

    results1 = db.search(user.name == 'alice')
    results1[0]['name'] = 'bob'

    results2 = db.search(user.name == 'alice')
    assert results2[0]['name'] == 'alice'


def test_ac2_mutating_nested_dict_does_not_affect_cached_search():
    """AC-2: results2[0]['details']['city'] is 'London'."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'details': {'city': 'London'}})
    user = Query()

    results1 = db.search(user.name == 'alice')
    results1[0]['details']['city'] = 'Paris'

    results2 = db.search(user.name == 'alice')
    assert results2[0]['details']['city'] == 'London'


def test_ac3_document_instance_and_metadata_preserved_on_search():
    """AC-3: results[0] is an instance of Document, results[0].doc_id is 1, and results[0] equals {'name': 'alice'}."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    user = Query()

    results = db.search(user.name == 'alice')
    assert isinstance(results[0], Document)
    assert results[0].doc_id == 1
    assert results[0] == {'name': 'alice'}


def test_ac4_empty_search_returns_empty_list():
    """AC-4: results is []."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    user = Query()

    results = db.search(user.name == 'bob')
    assert results == []
