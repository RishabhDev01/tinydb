import pytest
from tinydb import Query, TinyDB
from tinydb.operations import increment
from tinydb.storages import MemoryStorage


def test_update_error_memory_storage_leaves_documents_unchanged():
    """AC-1: Update error with MemoryStorage leaves documents unchanged (reproducing case)."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'count': 1})
    db.insert({'other': 0})
    db.insert({'count': 5})

    with pytest.raises(KeyError):
        db.update(increment('count'))

    assert db.all() == [{'count': 1}, {'other': 0}, {'count': 5}]


def test_update_error_conditional_query_leaves_documents_unchanged():
    """AC-2: Update error with conditional query leaves documents unchanged."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'group': 'a', 'val': 10})
    db.insert({'group': 'a', 'val': 'not_an_int'})

    with pytest.raises(TypeError):
        db.update(increment('val'), Query().group == 'a')

    assert db.all() == [{'group': 'a', 'val': 10}, {'group': 'a', 'val': 'not_an_int'}]


def test_update_error_with_doc_ids_leaves_documents_unchanged():
    """AC-3: Update error with doc_ids leaves documents unchanged."""
    db = TinyDB(storage=MemoryStorage)
    id1 = db.insert({'val': 10})
    id2 = db.insert({'other': 20})

    with pytest.raises(KeyError):
        db.update(increment('val'), doc_ids=[id1, id2])

    assert db.get(doc_id=1) == {'val': 10}


def test_successful_update_persists_modified_documents():
    """AC-4: Successful update persists modified documents."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'count': 1})
    db.insert({'count': 5})

    db.update(increment('count'))

    assert db.all() == [{'count': 2}, {'count': 6}]
