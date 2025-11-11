import logging


logger = logging.getLogger(__name__)


def search_usecase(
    storage,
    text: str,
    top_k: int | None,
    default_top_k: int,
    max_top_k: int,
    score_decimal_places: int,
) -> list[dict]:
    actual_top_k = top_k or default_top_k
    if actual_top_k > max_top_k:
        raise ValueError(f"top_k must be <= {max_top_k}")

    results = storage.search(query_text=text, top_k=actual_top_k)
    logger.info(
        "Search | len=%s | top_k=%s | found=%s",
        len(text),
        actual_top_k,
        len(results),
    )

    return [
        {
            "id": r.id,
            "score_rate": round(float(r.score), score_decimal_places),
            "text": r.text,
        }
        for r in results
    ]


def upsert_usecase(storage, text: str) -> dict:
    vector_id: int = storage.upsert(text)
    logger.info("Upserted ID: %s", vector_id)
    return {
        "id": vector_id,
        "status": "ok",
        "message": f"Upserted (ID: {vector_id})",
    }


def health_usecase(storage, model_name: str) -> dict:
    return {
        "status": "ok",
        "message": "Service is running",
        "model": model_name,
        "vectors_count": storage.count(),
    }

