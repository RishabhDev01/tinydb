import pytest
from tinydb import TinyDB, where
from tinydb.operations import append
from tinydb.storages import MemoryStorage


def test_append_existing_list():
    """AC-1: db.get(where('id') == 1) returns {'id': 1, 'tags': ['urgent', 'review']}."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 1, 'tags': ['urgent']})
    db.update(append('tags', 'review'), where('id') == 1)
    assert db.get(where('id') == 1) == {'id': 1, 'tags': ['urgent', 'review']}


def test_append_non_existent_field():
    """AC-2: db.get(where('id') == 2) returns {'id': 2, 'tags': ['urgent']}."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 2})
    db.update(append('tags', 'urgent'), where('id') == 2)
    assert db.get(where('id') == 2) == {'id': 2, 'tags': ['urgent']}


def test_append_non_list_field_raises_attribute_error():
    """AC-3: AttributeError is raised."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 3, 'tags': 'urgent'})
    with pytest.raises(AttributeError):
        db.update(append('tags', 'review'), where('id') == 3)


def test_append_multiple_documents():
    """AC-4: db.get(where('id') == 4) returns {'id': 4, 'count': 2}."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 4, 'count': 2})
    assert db.get(where('id') == 4) == {'id': 4, 'count': 2}
