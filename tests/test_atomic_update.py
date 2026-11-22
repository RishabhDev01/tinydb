"""Tests for atomic update behaviour (issue #3)."""

import json
import os
import tempfile
from tinydb import TinyDB
from tinydb.operations import increment
from tinydb.storages import MemoryStorage
from tinydb.storages import JSONStorage

# Helper to read JSON file content

def read_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# AC-1: No partial update on MemoryStorage

def test_memory_storage_atomic_update(db):
    """AC-1: No partial update on MemoryStorage."""
    # db fixture uses MemoryStorage by default
    assert db.all() == [{"count": 1}, {"other": 0}, {"count": 5}]
    try:
        db.update(increment("count"))
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")
    assert db.all() == [{"count": 1}, {"other": 0}, {"count": 5}]


# AC-2: No partial update on JSONStorage

def test_json_storage_atomic_update(tmp_path):
    """AC-2: No partial update on JSONStorage."""
    file_path = tmp_path / "db.json"
    db = TinyDB(str(file_path))
    db.insert_multiple([{"count": 1}, {"other": 0}, {"count": 5}])
    try:
        db.update(increment("count"))
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError")
    db.close()
    db = TinyDB(str(file_path))
    assert db.all() == [{"count": 1}, {"other": 0}, {"count": 5}]


# AC-3: Successful update when all documents have the field

def test_successful_update(db):
    """AC-3: Successful update when all documents have the field."""
    db.truncate()
    db.insert_multiple([{"count": 1}, {"count": 5}])
    result = db.update(increment("count"))
    assert result == 2
    assert db.all() == [{"count": 2}, {"count": 6}]


# AC-4: No change when no document matches the query

def test_no_match_update(db):
    """AC-4: No change when no document matches the query."""
    db.truncate()
    db.insert({"count": 3})
    result = db.update(increment("count"), where("missing") == True)
    assert result == 0
    assert db.all() == [{"count": 3}]
"""
