from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_pluck_names():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'name': 'a'}, {'name': 'b'}, {'name': 'c'}])
    assert db.pluck('name') == ['a', 'b', 'c']


def test_pluck_other_table():
    db = TinyDB(storage=MemoryStorage)
    db.table('users').insert({'email': 'x@example.com'})
    assert db.table('users').pluck('email') == ['x@example.com']
