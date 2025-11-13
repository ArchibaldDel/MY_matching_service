import logging
import sqlite3
import threading
from contextlib import contextmanager
from collections.abc import Generator

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, db_path: str = "vectors.db") -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._connect()
        self._initialize_schema()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-64000")
        logger.info("Connected to database: %s (WAL mode)", self._db_path)

    def _initialize_schema(self) -> None:
        assert self._conn is not None
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vectors (
                        id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        vector BLOB NOT NULL,
                        dim INTEGER NOT NULL,
                        count INTEGER NOT NULL DEFAULT 1,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """
                )
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_text ON vectors(text)")
                self._conn.execute("COMMIT")
                logger.debug("Database schema initialized")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    @contextmanager
    def transaction(self, mode: str = "DEFERRED") -> Generator[sqlite3.Connection, None, None]:
        if self._conn is None:
            raise RuntimeError("Database connection is not established")
        with self._lock:
            self._conn.execute(f"BEGIN {mode}")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    @contextmanager
    def read_transaction(self) -> Generator[sqlite3.Connection, None, None]:
        if self._conn is None:
            raise RuntimeError("Database connection is not established")
        with self._lock:
            try:
                yield self._conn
            except Exception:
                raise

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.info("Database connection closed")

