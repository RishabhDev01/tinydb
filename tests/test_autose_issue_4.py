from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def test_ac1_remove_documents_with_string_doc_ids():
    """AC-1: Remove documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'a'})
    assert doc_id == 1

    result = table.remove(doc_ids=['1'])
    assert result == [1]
    assert table.all() == []


def test_ac2_update_documents_with_string_doc_ids():
    """AC-2: Update documents with string doc_ids."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'a'})
    assert doc_id == 1

    result = table.update({'name': 'b'}, doc_ids=['1'])
    assert result == [1]
    assert table.get(doc_id=1) == Document({'name': 'b'}, doc_id=1)


def test_ac3_get_document_with_string_doc_id_returns_integer_doc_id():
    """AC-3: Get document with string doc_id returns integer doc_id attribute."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'a'})
    assert doc_id == 1

    doc = table.get(doc_id='1')
    assert doc == Document({'name': 'a'}, doc_id=1)
    assert doc.doc_id == 1
    assert isinstance(doc.doc_id, int) is True


def test_ac4_integer_doc_ids_behaviour_unchanged():
    """AC-4: Integer doc_ids behaviour unchanged."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'a'})
    assert doc_id == 1

    result = table.remove(doc_ids=[1])
    assert result == [1]
    assert table.all() == []


def test_ac5_non_existent_or_non_matching_string_doc_id():
    """AC-5: Non-existent or non-matching string doc_id returns empty result."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('_default')
    doc_id = table.insert({'name': 'a'})
    assert doc_id == 1

    result = table.remove(doc_ids=['999'])
    assert result == []
    assert len(table) == 1
