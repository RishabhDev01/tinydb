import pytest
from tinydb import TinyDB, Query, where
from tinydb.operations import increment
from tinydb.storages import MemoryStorage


def test_update_failure_leaves_documents_unmodified_memory_storage():
    """AC-1: Failed update operations leave stored documents unmodified."""
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'count': 1}, {'other': 0}, {'count': 5}])

    with pytest.raises(KeyError):
        db.update(increment('count'))

    assert db.all() == [{'count': 1}, {'other': 0}, {'count': 5}]


def test_update_failure_with_custom_callable_leaves_documents_unmodified():
    """AC-2: Failed custom callable update leaves documents unmodified."""
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([
        {'group': 'a', 'val': 10},
        {'group': 'a', 'val': 'not_an_int'},
    ])

    def updater(doc):
        doc['val'] += 5

    with pytest.raises(TypeError):
        db.update(updater, where('group') == 'a')

    assert db.all() == [
        {'group': 'a', 'val': 10},
        {'group': 'a', 'val': 'not_an_int'},
    ]


def test_update_failure_with_doc_ids_leaves_documents_unmodified():
    """AC-3: Failed update by doc_ids leaves documents unmodified."""
    db = TinyDB(storage=MemoryStorage)
    doc_id1 = db.insert({'val': 10})
    doc_id2 = db.insert({'val': 'text'})

    def updater(doc):
        doc['val'] = doc['val'] + 1

    with pytest.raises(TypeError):
        db.update(updater, doc_ids=[doc_id1, doc_id2])

    assert db.get(doc_id=doc_id1) == {'val': 10}


def test_successful_update_persists_changes():
    """AC-4: Successful updates persist correctly."""
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'count': 1}, {'count': 5}])

    db.update(increment('count'))

    assert db.all() == [{'count': 2}, {'count': 6}]
