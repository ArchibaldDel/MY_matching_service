#!/usr/bin/env python3
"""
Скрипт для тестирования поиска похожих товаров.

Использование:
    python scripts/test_search.py
    python scripts/test_search.py --text "адаптер ELM327"
    python scripts/test_search.py --random --top-k 10
    python scripts/test_search.py --load-test --count 1000
"""

import argparse
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

import httpx
from tqdm.asyncio import tqdm


def get_random_product_from_db(db_path: Path) -> tuple[int, str] | None:
    """Получает случайный товар из БД."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text FROM vectors ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
        return None
    except sqlite3.Error as e:
        print(f"❌ Ошибка чтения БД: {e}")
        return None


def get_products_from_db(db_path: Path, limit: int, offset: int = 0) -> list[tuple[int, str]]:
    """Получает товары из БД подряд."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, text FROM vectors ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"❌ Ошибка чтения БД: {e}")
        return []


def search_products(base_url: str, query_text: str, top_k: int = 5) -> list[dict] | None:
    """Выполняет поиск через API."""
    try:
        response = httpx.get(
            f"{base_url}/search",
            params={"text": query_text, "top_k": top_k},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP ошибка: {e.response.status_code}")
        try:
            error_detail = e.response.json()
            print(f"   Детали: {error_detail.get('detail', '')}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None


async def search_products_async(client: httpx.AsyncClient, base_url: str, query_text: str, top_k: int = 5) -> tuple[bool, float, int]:
    """Асинхронный поиск. Возвращает (успех, время, количество результатов)."""
    start_time = time.time()
    try:
        response = await client.get(
            f"{base_url}/search",
            params={"text": query_text, "top_k": top_k},
            timeout=30.0,
        )
        response.raise_for_status()
        results = response.json()
        elapsed = time.time() - start_time
        return True, elapsed, len(results) if results else 0
    except Exception:
        elapsed = time.time() - start_time
        return False, elapsed, 0


def print_results(query_id: int | None, query_text: str, results: list[dict]) -> None:
    """Выводит результаты поиска."""
    print("=" * 80)
    print("🔍 РЕЗУЛЬТАТЫ ПОИСКА")
    print("=" * 80)
    if query_id:
        print(f"Запрос (ID {query_id}): {query_text[:100]}...")
    else:
        print(f"Запрос: {query_text[:100]}...")
    print(f"Найдено результатов: {len(results)}\n")
    
    if not results:
        print("⚠️  Результаты не найдены")
        return
    
    for i, item in enumerate(results, 1):
        print(f"{i}. ID: {item['id']} | Score: {item['score_rate']:.4f}")
        print(f"   Текст: {item['text'][:150]}...")
        print()


async def load_test(base_url: str, db_path: Path, count: int, top_k: int, workers: int) -> None:
    """Нагрузочное тестирование поиска."""
    print(f"📖 Загружаем {count} товаров из БД...")
    products = get_products_from_db(db_path, count)
    
    if not products:
        print("❌ БД пуста или недоступна")
        return
    
    if len(products) < count:
        print(f"⚠️  В БД только {len(products)} товаров, будет протестировано {len(products)}")
        count = len(products)
    
    print(f"✅ Загружено {count} товаров\n")
    print(f"🚀 Начинаем нагрузочное тестирование:")
    print(f"   Товаров: {count}")
    print(f"   Top-K: {top_k}")
    print(f"   Воркеров: {workers}\n")
    
    stats = {"success": 0, "failed": 0, "total_time": 0.0, "total_results": 0}
    semaphore = asyncio.Semaphore(workers)
    
    async def test_one(product_id: int, query_text: str, pbar: tqdm) -> None:
        async with semaphore:
            async with httpx.AsyncClient() as client:
                success, elapsed, num_results = await search_products_async(client, base_url, query_text, top_k)
                pbar.update(1)
                if success:
                    stats["success"] += 1
                    stats["total_time"] += elapsed
                    stats["total_results"] += num_results
                else:
                    stats["failed"] += 1
    
    pbar = tqdm(total=count, desc="Тестирование", unit="запрос")
    start_time = time.time()
    
    tasks = [test_one(product_id, query_text, pbar) for product_id, query_text in products]
    await asyncio.gather(*tasks)
    
    pbar.close()
    total_elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"📊 РЕЗУЛЬТАТЫ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    print(f"{'='*80}")
    print(f"Всего запросов:     {count}")
    print(f"Успешных:           {stats['success']} ✅")
    print(f"Ошибок:             {stats['failed']} ❌")
    print(f"Общее время:        {total_elapsed:.2f} сек")
    print(f"Среднее время:      {stats['total_time'] / stats['success']:.3f} сек/запрос" if stats['success'] > 0 else "N/A")
    print(f"RPS (запросов/сек): {count / total_elapsed:.2f}")
    print(f"Среднее результатов: {stats['total_results'] / stats['success']:.1f}" if stats['success'] > 0 else "N/A")
    print(f"{'='*80}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Тестирование поиска похожих товаров",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="URL сервиса (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Текст для поиска (если не указан, берется случайный из БД)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Использовать случайный товар из БД",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Количество результатов (default: 5)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/vectors.db"),
        help="Путь к БД (default: data/vectors.db)",
    )
    parser.add_argument(
        "--load-test",
        action="store_true",
        help="Нагрузочное тестирование (берет товары подряд из БД)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Количество товаров для нагрузочного теста (default: 1000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Количество параллельных воркеров для нагрузочного теста (default: 10)",
    )
    
    args = parser.parse_args()
    
    # Нагрузочное тестирование
    if args.load_test:
        if not args.db_path.exists():
            print(f"❌ БД не найдена: {args.db_path}")
            return 1
        asyncio.run(load_test(args.url, args.db_path, args.count, args.top_k, args.workers))
        return 0
    
    # Определяем текст для поиска
    query_id = None
    query_text = args.text
    
    if args.random or (not query_text and args.db_path.exists()):
        print("📖 Получаем случайный товар из БД...")
        result = get_random_product_from_db(args.db_path)
        if result:
            query_id, query_text = result
            print(f"✅ Выбран товар ID: {query_id}")
        else:
            print("❌ БД пуста или недоступна. Используйте --text для указания запроса.")
            if not query_text:
                return 1
    
    if not query_text:
        print("❌ Не указан текст для поиска. Используйте --text или --random")
        return 1
    
    # Проверяем доступность сервера
    print(f"🔍 Проверяем доступность сервера: {args.url}")
    try:
        response = httpx.get(f"{args.url}/", timeout=5.0)
        response.raise_for_status()
        print("✅ Сервер доступен\n")
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        print("Убедитесь, что сервис запущен!")
        return 1
    
    # Выполняем поиск
    print(f"🚀 Выполняем поиск (top_k={args.top_k})...\n")
    results = search_products(args.url, query_text, args.top_k)
    
    if results is None:
        return 1
    
    # Выводим результаты
    print_results(query_id, query_text, results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

