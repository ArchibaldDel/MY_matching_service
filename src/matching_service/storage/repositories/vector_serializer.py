import numpy as np
import numpy.typing as npt


class VectorSerializer:
    @staticmethod
    def serialize(vector: npt.NDArray[np.float32]) -> bytes:
        return vector.astype(np.float32).tobytes()

    @staticmethod
    def deserialize(blob: bytes, dim: int) -> npt.NDArray[np.float32]:
        return np.frombuffer(blob, dtype=np.float32).reshape(dim)

