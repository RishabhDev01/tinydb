from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def test_remove_string_doc_ids():
    """AC-1: Remove documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=['1'])
    assert result == [1]
    assert db.all() == []


def test_update_string_doc_ids():
    """AC-2: Update documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.update({'name': 'b'}, doc_ids=['1'])
    assert result == [1]
    doc = db.get(doc_id=1)
    assert doc == Document({'name': 'b'}, doc_id=1)


def test_get_string_doc_id():
    """AC-3: Get document with string doc_id returns integer doc_id attribute."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    doc = db.get(doc_id='1')
    assert doc == Document({'name': 'a'}, doc_id=1)
    assert doc.doc_id == 1
    assert isinstance(doc.doc_id, int) is True


def test_remove_integer_doc_ids_unchanged():
    """AC-4: Integer doc_ids behaviour unchanged."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=[1])
    assert result == [1]
    assert db.all() == []


def test_remove_nonexistent_string_doc_id():
    """AC-5: Non-existent or non-matching string doc_id returns empty result."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    result = db.remove(doc_ids=['999'])
    assert result == []
    assert len(db) == 1
