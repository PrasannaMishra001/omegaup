'''Reusable mock cursor and connection for cron unit tests.

The real `lib.db.Connection.cursor()` returns a context manager that yields a
`mysql.connector.cursor.MySQLCursor`. Cron code typically does:

    with dbconn.cursor() as cur:
        cur.execute(SQL, params)
        for row in cur.fetchall():
            ...

and sometimes calls `dbconn.conn.commit()` / `dbconn.conn.rollback()` directly.

`MockCursor` and `MockConnection` mimic exactly that shape, so existing cron
functions can be exercised without any source changes. Match resolution uses
substring search on the normalized (whitespace collapsed, lower-cased) SQL,
which is robust to the multi-line formatting cron queries use.
'''
from typing import (Any, Dict, Iterable, Iterator, List, Optional, Sequence,
                    Tuple, Union)

Row = Union[Tuple[Any, ...], Dict[str, Any]]
Script = Sequence[Tuple[str, Sequence[Row]]]


def _normalize(sql: str) -> str:
    '''Collapse whitespace and lowercase so substring matches survive
    multi-line SQL formatting changes.'''
    return ' '.join(sql.lower().split())


class MockCursor:
    '''Programmable stand-in for `mysql.connector.cursor.MySQLCursor`.

    Configure with a sequence of `(sql_substring, rows)` pairs. On each
    `execute()` the first substring that appears in the normalized query
    wins, and the matching `rows` become the result set for `fetchall()`,
    `fetchone()` and iteration. Every executed `(sql, params)` pair is
    appended to `calls` for assertion in tests.
    '''

    def __init__(
        self,
        script: Optional[Script] = None,
        dictionary: bool = False,
    ) -> None:
        self._script: List[Tuple[str, Sequence[Row]]] = list(script or [])
        self._dictionary = dictionary
        self._current: Sequence[Row] = []
        self.calls: List[Tuple[str, Any]] = []

    def execute(self, sql: str, params: Any = None) -> None:
        '''Record the call and resolve a result set from the script.'''
        self.calls.append((sql, params))
        normalized = _normalize(sql)
        for substring, rows in self._script:
            if substring.lower() in normalized:
                self._current = rows
                return
        self._current = []

    def executemany(self, sql: str, seq_of_params: Iterable[Any]) -> None:
        '''Forward each parameter row through `execute` so `calls` stays
        a faithful record of every parameterized batch insert.'''
        for params in seq_of_params:
            self.execute(sql, params)

    def fetchall(self) -> List[Row]:
        '''Return the currently scripted result set.'''
        return list(self._current)

    def fetchone(self) -> Optional[Row]:
        '''Return the first row of the scripted result set, or None.'''
        return self._current[0] if self._current else None

    def __iter__(self) -> Iterator[Row]:
        return iter(self._current)

    def __enter__(self) -> 'MockCursor':
        return self

    def __exit__(self, *exc: Any) -> None:
        del exc


class MockConnection:
    '''Stand-in for `lib.db.Connection`.

    Holds a read-write cursor and an optional read-only cursor, mirroring
    the real two-cursor split that most cron code relies on. Records
    `commits` and `rollbacks` so tests can assert transactional behavior.
    Sets `conn = self` so call sites like `dbconn.conn.commit()` work.
    '''

    def __init__(
        self,
        cur: MockCursor,
        cur_readonly: Optional[MockCursor] = None,
    ) -> None:
        self._cur = cur
        self._cur_ro = cur_readonly or cur
        self.commits = 0
        self.rollbacks = 0
        self.conn = self

    def cursor(
        self,
        buffered: bool = False,
        dictionary: bool = False,
    ) -> MockCursor:
        del buffered, dictionary
        return self._cur

    def readonly_cursor(self) -> MockCursor:
        '''Some cron call sites manage two cursors explicitly. This helper
        returns the read-only one without forcing tests to introspect.'''
        return self._cur_ro

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        pass
