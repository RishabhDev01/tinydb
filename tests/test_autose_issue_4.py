import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def test_remove_string_doc_ids():
    """AC-1: the call returns [1] and table.all() returns []."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=['1'])
    assert result == [1]
    assert isinstance(result[0], int)
    assert db.all() == []


def test_update_string_doc_ids():
    """AC-2: the call returns [1] and table.get(doc_id=1) returns Document({'name': 'b'}, doc_id=1)."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.update({'name': 'b'}, doc_ids=['1'])
    assert result == [1]
    assert isinstance(result[0], int)
    doc = db.get(doc_id=1)
    assert doc == Document({'name': 'b'}, doc_id=1)
    assert doc.doc_id == 1


def test_get_string_doc_id_returns_int_id():
    """AC-3: the return value is Document({'name': 'a'}, doc_id=1) with doc.doc_id == 1 and isinstance(doc.doc_id, int)."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    doc = db.get(doc_id='1')
    assert doc == Document({'name': 'a'}, doc_id=1)
    assert doc.doc_id == 1
    assert isinstance(doc.doc_id, int)


def test_remove_mixed_int_and_string_doc_ids():
    """AC-4: the call returns [1] and table.all() returns []."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=[1, '1'])
    assert result == [1]
    assert isinstance(result[0], int)
    assert db.all() == []


def test_remove_unconvertible_string_doc_ids():
    """AC-5: the call returns [] and len(table) returns 1."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=['not_an_id', 'invalid'])
    assert result == []
    assert len(db) == 1
