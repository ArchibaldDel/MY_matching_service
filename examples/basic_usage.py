import logging

from matching_service.config import Config
from matching_service.services import TextEmbedder, VectorStorage
from matching_service.storage.repositories import SqliteVectorRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    config = Config()

    repository = SqliteVectorRepository(db_path=str(config.db.vector_db_path))

    embedder = TextEmbedder(
        model_name=config.ml.model_name,
        device=config.ml.device,
        max_text_length=config.ml.max_text_length,
        min_clamp_value=config.ml.min_clamp_value,
    )

    storage = VectorStorage(
        repository=repository,
        embedding_batch_size=config.ml.embedding_batch_size,
        embedder=embedder,
    )

    print(f"Storage initialized with {storage.count()} vectors")

    if storage.count() == 0:
        print("\nNo vectors in storage. Adding sample data...")
        storage.upsert("Масло моторное 5W-40 синтетическое")
        storage.upsert("Фильтр масляный для двигателя")
        storage.upsert("Свечи зажигания NGK")
        print(f"Added sample data. Total vectors: {storage.count()}")

    query = "моторное масло"
    top_k = 5

    print(f"\n{'=' * 70}")
    print(f"Searching for: '{query}' (top_k={top_k})")
    print(f"{'=' * 70}")

    results = storage.search(query, top_k=top_k)

    for i, result in enumerate(results, 1):
        print(f"{i}. [ID: {result.id}] Score: {result.score:.4f}")
        print(f"   {result.text[:100]}...")
        print()


if __name__ == "__main__":
    main()
