import numpy.typing as npt

from matching_service.storage.repositories.connection import DatabaseConnection
from matching_service.storage.repositories.vector_reader import VectorReader
from matching_service.storage.repositories.vector_writer import VectorWriter


class SqliteVectorRepository:
    def __init__(self, db_path: str = "vectors.db") -> None:
        self._db = DatabaseConnection(db_path)
        self._reader = VectorReader(self._db)
        self._writer = VectorWriter(self._db)

    def get_all_vectors(self) -> tuple[list[int], list[str], npt.NDArray]:
        return self._reader.get_all_vectors()

    def upsert(self, vector_id: int, text: str, vector: npt.NDArray) -> tuple[int, bool]:
        return self._writer.upsert(vector_id, text, vector)

    def close(self) -> None:
        self._db.close()

