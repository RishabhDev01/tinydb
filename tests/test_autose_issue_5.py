"""Acceptance tests for Table.pluck method."""

import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_all_present():
    """AC-1: the return value is ['alice', 'bob']."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 20})
    db.insert({'name': 'bob', 'age': 25})
    assert db.pluck('name') == ['alice', 'bob']


def test_pluck_missing_field_skipped():
    """AC-2: the return value is ['alice', 'charlie']."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'alice', 'age': 20})
    db.insert({'age': 25})
    db.insert({'name': 'charlie', 'age': 30})
    assert db.pluck('name') == ['alice', 'charlie']


def test_pluck_none_and_other_values():
    """AC-3: the return value is [None, 42]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'val': None})
    db.insert({'val': 42})
    assert db.pluck('val') == [None, 42]


def test_pluck_empty_table():
    """AC-4: the return value is []."""
    db = TinyDB(storage=MemoryStorage)
    assert db.pluck('name') == []


def test_pluck_table_named():
    """AC-5: the return value is ['alice@example.com', 'bob@example.com']."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('users')
    table.insert({'email': 'alice@example.com'})
    table.insert({'email': 'bob@example.com'})
    assert table.pluck('email') == ['alice@example.com', 'bob@example.com']
