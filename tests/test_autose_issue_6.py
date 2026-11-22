import pytest
from tinydb import TinyDB, where
from tinydb.operations import append, increment
from tinydb.storages import MemoryStorage


def test_append_to_existing_list():
    """AC-1: Append to existing list field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 1, 'tags': ['urgent']})

    db.update(append('tags', 'review'), where('id') == 1)

    assert db.get(where('id') == 1) == {'id': 1, 'tags': ['urgent', 'review']}


def test_append_to_non_existent_field():
    """AC-2: Append to non-existent field initializes list."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 2})

    db.update(append('tags', 'urgent'), where('id') == 2)

    assert db.get(where('id') == 2) == {'id': 2, 'tags': ['urgent']}


def test_append_to_non_list_raises_attribute_error():
    """AC-3: Append to field with non-list value raises AttributeError."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 3, 'tags': 'urgent'})

    with pytest.raises(AttributeError):
        db.update(append('tags', 'review'), where('id') == 3)


def test_existing_operations_unchanged():
    """AC-4: Existing operations remain unchanged."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 4, 'count': 1})

    db.update(increment('count'), where('id') == 4)

    assert db.get(where('id') == 4) == {'id': 4, 'count': 2}
