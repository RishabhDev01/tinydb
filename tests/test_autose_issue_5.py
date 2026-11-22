import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_all_matching():
    """AC-1: the return value is ['alice', 'bob']."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})
    assert db.pluck('name') == ['alice', 'bob']


def test_pluck_skipping_missing():
    """AC-2: the return value is ['alice', 'charlie']."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 20})
    db.insert({'age': 30})
    db.insert({'name': 'charlie', 'age': 25})
    assert db.pluck('name') == ['alice', 'charlie']


def test_pluck_with_none_value():
    """AC-3: the return value is [None, 42]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'val': None})
    db.insert({'val': 42})
    assert db.pluck('val') == [None, 42]


def test_pluck_empty_or_nonexistent_field():
    """AC-4: the return value is []."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice'})
    db.insert({'name': 'bob'})
    assert db.pluck('nonexistent') == []


def test_pluck_on_custom_table():
    """AC-5: the return value is ['alice@example.com', 'bob@example.com']."""
    db = TinyDB(storage=MemoryStorage)
    users = db.table('users')
    users.insert({'email': 'alice@example.com'})
    users.insert({'email': 'bob@example.com'})
    assert users.pluck('email') == ['alice@example.com', 'bob@example.com']
