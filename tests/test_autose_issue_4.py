from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def test_ac1_remove_documents_with_string_doc_ids():
    """AC-1: Remove documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    removed = db.remove(doc_ids=['1'])

    assert removed == [1]
    assert db.all() == []


def test_ac2_update_documents_with_string_doc_ids():
    """AC-2: Update documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    updated = db.update({'name': 'b'}, doc_ids=['1'])

    assert updated == [1]
    doc = db.get(doc_id=1)
    assert doc == Document({'name': 'b'}, doc_id=1)


def test_ac3_get_document_with_string_doc_id_returns_integer_doc_id_attribute():
    """AC-3: Get document with string doc_id returns integer doc_id attribute."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    doc = db.get(doc_id='1')

    assert doc == Document({'name': 'a'}, doc_id=1)
    assert doc.doc_id == 1
    assert isinstance(doc.doc_id, int) is True


def test_ac4_integer_doc_ids_behaviour_unchanged():
    """AC-4: Integer doc_ids behaviour unchanged."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    removed = db.remove(doc_ids=[1])

    assert removed == [1]
    assert db.all() == []


def test_ac5_non_existent_or_non_matching_string_doc_id_returns_empty_result():
    """AC-5: Non-existent or non-matching string doc_id returns empty result."""
    db = TinyDB(storage=MemoryStorage)
    doc_id = db.insert({'name': 'a'})
    assert doc_id == 1

    removed = db.remove(doc_ids=['999'])

    assert removed == []
    assert len(db) == 1
