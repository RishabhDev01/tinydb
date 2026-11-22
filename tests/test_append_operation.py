from tinydb import TinyDB, where
from tinydb.operations import append
from tinydb.storages import MemoryStorage


def test_append_to_existing_list():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 7, 'tags': ['a']})
    db.update(append('tags', 'urgent'), where('id') == 7)
    assert db.get(where('id') == 7)['tags'] == ['a', 'urgent']


def test_append_appends_in_order():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'id': 1, 'tags': []})
    db.update(append('tags', 'x'), where('id') == 1)
    db.update(append('tags', 'y'), where('id') == 1)
    assert db.get(where('id') == 1)['tags'] == ['x', 'y']
