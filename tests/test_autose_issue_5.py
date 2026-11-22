"""Tests for Table.pluck functionality."""
from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_all_matching_keys():
    """AC-1: Pluck field from documents with all matching keys."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('test')
    table.insert({'name': 'Alice', 'age': 30})
    table.insert({'name': 'Bob', 'age': 25})

    assert table.pluck('name') == ['Alice', 'Bob']


def test_pluck_skip_missing_field():
    """AC-2: Skip documents lacking the plucked field."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('test')
    table.insert({'name': 'Alice', 'score': 100})
    table.insert({'score': 85})
    table.insert({'name': 'Charlie', 'score': 90})

    assert table.pluck('name') == ['Alice', 'Charlie']


def test_pluck_none_vs_absent():
    """AC-3: Pluck when field value is None vs absent."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('test')
    table.insert({'name': 'Alice', 'alias': None})
    table.insert({'name': 'Bob'})

    assert table.pluck('alias') == [None]


def test_pluck_empty_table():
    """AC-4: Pluck from an empty table."""
    db = TinyDB(storage=MemoryStorage)
    table = db.table('test')

    assert table.pluck('name') == []


def test_pluck_default_table():
    """AC-5: Pluck via default table on TinyDB instance."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'city': 'Paris'})
    db.insert({'city': 'London'})

    assert db.pluck('city') == ['Paris', 'London']
