"""Tests for Table.pluck functionality."""

from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_all_present():
    """AC-1: Pluck field from documents with all fields present."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})

    result = db.pluck('name')
    assert result == ['alice', 'bob']


def test_pluck_skipping_missing():
    """AC-2: Pluck field skipping documents missing the field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 30})
    db.insert({'age': 25})
    db.insert({'name': 'charlie'})

    result = db.pluck('name')
    assert result == ['alice', 'charlie']


def test_pluck_preserves_none():
    """AC-3: Pluck preserves None values when key is present."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'val': None})
    db.insert({'val': 42})

    result = db.pluck('val')
    assert result == [None, 42]


def test_pluck_non_existent():
    """AC-4: Pluck non-existent field."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})

    result = db.pluck('missing')
    assert result == []


def test_pluck_custom_table():
    """AC-5: Pluck on a custom table."""
    db = TinyDB(storage=MemoryStorage)
    users = db.table('users')
    users.insert({'email': 'alice@example.com'})
    users.insert({'email': 'bob@example.com'})

    result = db.table('users').pluck('email')
    assert result == ['alice@example.com', 'bob@example.com']
