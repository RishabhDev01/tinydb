from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_remove_with_string_id():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'a'})
    assert db.remove(doc_ids=['1']) == [1]
    assert db.all() == []


def test_remove_with_int_id_still_works():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'a'})
    assert db.remove(doc_ids=[1]) == [1]
