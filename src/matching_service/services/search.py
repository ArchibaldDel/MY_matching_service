import numpy as np
import numpy.typing as npt


def cosine_topk(
    query_embs: npt.NDArray[np.float32],
    corpus_embs: npt.NDArray[np.float32],
    k: int = 5,
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int32]]:
    sims: npt.NDArray[np.float32] = query_embs @ corpus_embs.T

    if sims.ndim == 1:
        sims = sims.reshape(1, -1)

    idx: npt.NDArray[np.int32] = np.argsort(-sims, axis=1)[:, :k].astype(np.int32)
    batch_indices: npt.NDArray[np.int32] = np.arange(sims.shape[0], dtype=np.int32)[:, np.newaxis]
    scores: npt.NDArray[np.float32] = sims[batch_indices, idx]

    return scores, idx
