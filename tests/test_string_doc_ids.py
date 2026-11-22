from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def _db():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'a'})
    return db


def test_remove_with_string_id():
    db = _db()
    assert db.remove(doc_ids=['1']) == [1]
    assert db.all() == []


def test_update_with_string_id():
    db = _db()
    assert db.update({'x': 1}, doc_ids=['1']) == [1]
    assert db.get(doc_id=1) == {'name': 'a', 'x': 1}


def test_get_with_string_id_returns_int_doc_id():
    doc = _db().get(doc_id='1')
    assert doc == {'name': 'a'} and doc.doc_id == 1


def test_unconvertible_ids_match_nothing():
    db = _db()
    assert db.remove(doc_ids=['abc', None]) == []
    assert len(db) == 1
