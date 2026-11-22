# TinyDB architecture

> Written for agents and contributors who need to **change** this code. Pinned at commit `edff96a` (v4.9.0). Read this before planning a change. The "Where to change what" table is the shortest path to the right file.

## 1. What TinyDB is

TinyDB is a pure-Python, single-process document database. A database is one Python `dict` of tables. Every write reads the **whole** dict from storage, changes it, and writes the **whole** dict back. There is no server, no index, no transaction log, and no thread safety.

## 2. Module map

| Module | Lines | Responsibility | Key names |
|---|---|---|---|
| `tinydb/__init__.py` | 33 | Public API re-exports | `TinyDB`, `Query`, `where`, `Storage`, `JSONStorage` |
| `tinydb/database.py` | 274 | `TinyDB`: owns the storage, manages tables, forwards to the default table | `TinyDB.table`, `tables`, `drop_table(s)`, `close`, `__getattr__` |
| `tinydb/table.py` | 854 | `Table` and `Document`: all CRUD, query cache, document IDs | `insert`, `insert_multiple`, `all`, `search`, `get`, `contains`, `update`, `update_multiple`, `upsert`, `remove`, `truncate`, `count`, `_read_table`, `_update_table`, `_get_next_id` |
| `tinydb/queries.py` | 535 | Query DSL: `Query().field == x` builds a `QueryInstance` (a callable plus a hash) | `QueryInstance`, `Query`, `_generate_test`, `where`, `exists`, `matches`, `search`, `test`, `any`, `all`, `one_of`, `fragment`, `noop`, `map` |
| `tinydb/storages.py` | 181 | Persistence back-ends | `Storage` (ABC: `read`, `write`, `close`), `JSONStorage`, `MemoryStorage`, `touch` |
| `tinydb/middlewares.py` | 142 | Wrappers around a storage | `Middleware`, `CachingMiddleware` (`WRITE_CACHE_SIZE`, `flush`) |
| `tinydb/operations.py` | 75 | Update helpers that return `transform(doc)` callables | `delete`, `add`, `subtract`, `set`, `increment`, `decrement` |
| `tinydb/utils.py` | 169 | Internal helpers | `LRUCache`, `FrozenDict`, `freeze`, `with_typehint` |
| `tinydb/mypy_plugin.py` | 39 | mypy plugin for `with_typehint` | — |

## 3. Runtime structure and data flow

```
TinyDB(path, storage=JSONStorage)            # database.py
 ├─ self._storage = storage(*args, **kwargs) # storages.py / middlewares.py
 └─ self._tables: {name: Table}              # created lazily by .table(name)
       Table(storage, name, cache_size)      # table.py
        ├─ _query_cache: LRUCache[QueryLike, list[Document]]
        └─ _next_id: int | None
```

**Storage data model** (what `Storage.read()` returns and `write()` takes):

```python
{ "<table name>": { "<doc_id as str>": {document fields...}, ... }, ... }
```

**Read path.** `Table.search(cond)`:
1. Return a copy of the cached result if `cond` is in the query cache.
2. Otherwise `_read_table()` → `storage.read()[name]`.
3. Wrap each matching document as `Document(doc, int(doc_id))`.
4. Cache the result if `cond.is_cacheable()`.

**Write path.** Every mutator (`insert`, `update`, `remove`, `upsert`, `truncate`) goes through `Table._update_table(updater)`:
1. `storage.read()`.
2. Convert the doc-id keys from `str` to `document_id_class` (`int`).
3. `updater(table)` mutates the dict in place.
4. Convert the keys back to `str`.
5. `storage.write(all_tables)`.
6. `clear_cache()`.

**Default-table forwarding.** `TinyDB.__getattr__` forwards any unknown attribute to `self.table('_default')`. So **a new public method added to `Table` is automatically available as `db.<method>`**. Magic methods (`__len__`, `__iter__`) are forwarded by hand in `database.py`.

**Query evaluation.** `Query().a.b == 1`:
1. `__getattr__` builds `_path = ('a', 'b')`.
2. `__eq__` calls `_generate_test(test, hashval)`.
3. That returns a `QueryInstance` whose `runner` walks the path. A `KeyError` or `TypeError` on the way means **no match** (returns `False`), not an exception.
4. `&`, `|` and `~` combine instances and their hashes.

## 4. Invariants (break these and tests fail)

1. **Every write must clear the query cache.** `_update_table` does this. Never write to storage from a `Table` method any other way.
2. **Doc IDs are `str` in storage and `int` in memory.** Convert at the boundary, as `_update_table` and `search` do. Inside `Table` the two forms meet, so check which dict you are indexing:
   - **`_read_table()` returns the raw storage dict, so its keys are `str`.** Read paths (`get`, `search`, `__iter__`; `contains` goes through `get`) look up `str(doc_id)` (e.g. `table.get(str(doc_id))`) and wrap results as `Document(doc, self.document_id_class(key))`.
   - **The `updater(table)` passed to `_update_table` sees keys already converted to `document_id_class` (`int`).** Write paths (`insert`, `update`, `remove`; `upsert` goes through `update`) compare against `int` IDs.
   - A caller's ID (e.g. `'1'` or `1`) must be converted to the form of the dict it indexes: `str(...)` for `_read_table()`, `document_id_class(...)` inside an updater. Values that cannot be converted (e.g. `float('nan')`) must simply match nothing (see `test_get_ids`).
3. **`search()` returns a fresh list, but the cached `Document` objects are shared.** Callers must not mutate them.
4. **`_next_id` is a cache.** `truncate()` resets it to `None`. Any new method that removes all documents must do the same.
5. **Queries must be hashable** to be cached. `Query.test(func)` and `Query.map(fn)` are only cacheable if `func` is hashable.
6. **An empty `Query()` must never be evaluated.** It raises `RuntimeError('Empty query was evaluated')`. `_generate_test` raises `ValueError('Query has no path')`.
7. **`Storage.read()` returns `None` for an empty database**, not `{}`. Callers handle both.
8. **`CachingMiddleware` only writes to the real storage on `flush()`/`close()`**, or after `WRITE_CACHE_SIZE` writes.

## 5. Where to change what

| If the change is about… | Edit | Usually also |
|---|---|---|
| a new Table operation (e.g. counting, plucking, aggregation) | `tinydb/table.py` → new method on `Table` | nothing in `database.py` (forwarded automatically); tests in `tests/test_tables.py` or `tests/test_tinydb.py` |
| behaviour of `get`, `contains`, `update`, `remove`, `upsert` | `tinydb/table.py` (that method) | overloads near `get` (lines ~300–340) if signatures change |
| a new query operator or test | `tinydb/queries.py` → method on `Query` using `_generate_test` with a unique `hashval` tuple | `tests/test_queries.py` |
| how fields or nested paths are resolved | `Query._generate_test.runner` | all query tests |
| a new update helper (`db.update(op(...))`) | `tinydb/operations.py` | `tests/test_operations.py` |
| file format, encoding, file creation | `tinydb/storages.py` → `JSONStorage` | `tests/test_storages.py` |
| a new storage back-end | subclass `Storage` in `tinydb/storages.py` | export it in `__init__.py` if it is public |
| caching or flushing behaviour | `tinydb/middlewares.py` → `CachingMiddleware` | `tests/test_middlewares.py` |
| table management (create, list, drop tables) | `tinydb/database.py` → `TinyDB` | `tests/test_tinydb.py` |
| the LRU query cache | `tinydb/utils.py` → `LRUCache` | `tests/test_utils.py` |

## 6. Tests

- Run them with `python -m pytest -q`. Baseline at `edff96a`: **227 passed, 1 skipped, about 2 s**.
- `pytest.ini` adds `--cov tinydb`, so **`pytest-cov` must be installed**.
- **The `db` fixture** (`tests/conftest.py`) is parametrised over `memory` and `json`. Every test that uses it runs twice. It starts with 3 documents: `{'int': 1, 'char': 'a'|'b'|'c'}`. Tests must hold for both storages.
- **The `storage` fixture** is `CachingMiddleware(MemoryStorage)()`.
- Test files mirror the modules: `test_tables.py`, `test_queries.py`, `test_storages.py`, `test_middlewares.py`, `test_operations.py`, `test_utils.py`, and `test_tinydb.py` (end-to-end through `TinyDB`).
- Style: plain `def test_x(db):` functions, `with pytest.raises(...)` for errors. There are no test classes.

## 7. Conventions

- Python ≥ 3.10. Type hints on public methods. mypy runs in CI on one Python version (`mypy.ini`).
- PEP 8 via `pycodestyle`. Lines are at most 79 characters.
- Public methods have a reST docstring with `:param:` and `:returns:`. New public API gets a `.. versionadded::` note in its docstring.
- Errors: `ValueError` for bad arguments, `KeyError` is not raised to users from queries, `RuntimeError` for an empty query.
- No new runtime dependencies. TinyDB has none.

## 8. Known sharp edges

- `Table.get` has many `@overload`s. Change all of them together with the implementation.
- `update()` and `remove()` accept `cond` **or** `doc_ids`. Both paths must be kept.
- `JSONStorage` takes `**kwargs` that go straight to `json.dumps`. Never route untrusted input there.
- `TinyDB.__getattr__` hides typos: `db.serch(...)` raises an `AttributeError` that mentions `Table`, not `TinyDB`.
