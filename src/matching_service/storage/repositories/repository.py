import numpy.typing as npt

from matching_service.storage.repositories.connection import DatabaseConnection
from matching_service.storage.repositories.vector_reader import VectorReader
from matching_service.storage.repositories.vector_writer import VectorWriter


class SqliteVectorRepository:
    def __init__(self, db_path: str = "vectors.db") -> None:
        self._db = DatabaseConnection(db_path)
        self._reader = VectorReader(self._db)
        self._writer = VectorWriter(self._db)

    def get_by_id(self, vector_id: int) -> tuple[str, npt.NDArray] | None:
        return self._reader.get_by_id(vector_id)

    def get_by_text(self, text: str) -> tuple[int, npt.NDArray] | None:
        return self._reader.get_by_text(text)

    def get_all_vectors(self) -> tuple[list[int], list[str], npt.NDArray]:
        return self._reader.get_all_vectors()

    def exists(self, text: str) -> bool:
        return self._reader.exists(text)

    def count(self) -> int:
        return self._reader.count()

    def insert(self, vector_id: int, text: str, vector: npt.NDArray) -> int:
        return self._writer.insert(vector_id, text, vector)

    def update(self, vector_id: int, text: str, vector: npt.NDArray) -> int:
        return self._writer.update(vector_id, text, vector)

    def upsert(self, vector_id: int, text: str, vector: npt.NDArray) -> tuple[int, bool]:
        return self._writer.upsert(vector_id, text, vector)

    def delete(self, text: str) -> bool:
        return self._writer.delete(text)

    def batch_insert(
        self, ids: list[int], texts: list[str], vectors: npt.NDArray, batch_size: int = 100
    ) -> list[int]:
        return self._writer.batch_insert(ids, texts, vectors, batch_size)

    def close(self) -> None:
        self._db.close()

    @property
    def reader(self) -> VectorReader:
        return self._reader

    @property
    def writer(self) -> VectorWriter:
        return self._writer

