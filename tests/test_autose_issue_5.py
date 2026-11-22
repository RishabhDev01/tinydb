"""Tests for the Table.pluck method."""

from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_all_present():
    """AC-1: Pluck field from documents with all fields present."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})

    assert db.pluck('name') == ['alice', 'bob']


def test_pluck_skipping_missing():
    """AC-2: Pluck field skipping documents missing the field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 30})
    db.insert({'age': 25})
    db.insert({'name': 'charlie'})

    assert db.pluck('name') == ['alice', 'charlie']


def test_pluck_preserves_none():
    """AC-3: Pluck preserves None values when key is present."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'val': None})
    db.insert({'val': 42})

    assert db.pluck('val') == [None, 42]


def test_pluck_non_existent():
    """AC-4: Pluck non-existent field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})

    assert db.pluck('missing') == []


def test_pluck_custom_table():
    """AC-5: Pluck on a custom table."""
    db = TinyDB(storage=MemoryStorage)
    users = db.table('users')
    users.insert({'email': 'alice@example.com'})
    users.insert({'email': 'bob@example.com'})

    assert users.pluck('email') == ['alice@example.com', 'bob@example.com']
