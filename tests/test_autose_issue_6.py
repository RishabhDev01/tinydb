import pytest
from tinydb import TinyDB, where
from tinydb.operations import append, increment
from tinydb.storages import MemoryStorage


def test_append_existing_list():
    """AC-1: Append to existing list field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 1, 'tags': ['urgent']})

    db.update(append('tags', 'review'), where('id') == 1)

    assert db.get(where('id') == 1) == {'tags': ['urgent', 'review'], 'id': 1}


def test_append_field_not_exists():
    """AC-2: Append when field does not exist."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 2})

    db.update(append('tags', 'urgent'), where('id') == 2)

    assert db.get(where('id') == 2) == {'tags': ['urgent'], 'id': 2}


def test_append_non_list_raises_attribute_error():
    """AC-3: Append to non-list existing field raises AttributeError."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 3, 'tags': 42})

    with pytest.raises(AttributeError):
        db.update(append('tags', 'urgent'), where('id') == 3)


def test_existing_update_operations_unchanged():
    """AC-4: Existing update operations unchanged."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 4, 'count': 1})

    db.update(increment('count'), where('id') == 4)

    assert db.get(where('id') == 4) == {'id': 4, 'count': 2}
