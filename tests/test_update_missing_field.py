from tinydb import TinyDB
from tinydb.operations import increment
from tinydb.storages import MemoryStorage


def test_increment_with_missing_field_does_not_raise():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'count': 1})
    db.insert({'other': 0})
    db.insert({'count': 5})
    db.update(increment('count'))
    assert [d.get('count') for d in db.all()] == [2, None, 6]


def test_increment_all_fields_present():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'count': 1}, {'count': 2}])
    db.update(increment('count'))
    assert [d['count'] for d in db.all()] == [2, 3]
