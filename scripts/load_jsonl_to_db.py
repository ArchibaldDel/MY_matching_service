#!/usr/bin/env python3
"""
Скрипт для загрузки данных из JSONL файла в векторную БД через API.

Использование:
    python scripts/load_jsonl_to_db.py data/KE_Автотовары_1000.jsonl
    python scripts/load_jsonl_to_db.py data/KE_Автотовары.jsonl --batch-size 50 --workers 10
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from tqdm.asyncio import tqdm


def format_product_text(product: dict[str, Any]) -> str:
    """Формирует текстовое представление товара для векторизации."""
    parts = []
    
    # Название (обязательное)
    if title := product.get("title", "").strip():
        parts.append(f"Название: {title}")
    
    # Категории
    categories = []
    for cat_key in ["greatgrandparent_category", "grandparent_category", "parent_category", "category"]:
        if cat_val := product.get(cat_key):
            if cat_val not in categories:
                categories.append(cat_val)
    if categories:
        parts.append(f"Категории: {' > '.join(categories)}")
    
    # Описание (очищенное от HTML)
    if desc := product.get("description", "").strip():
        # Простая очистка HTML тегов
        import re
        clean_desc = re.sub(r'<[^>]+>', ' ', desc)
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
        if clean_desc:
            parts.append(f"Описание: {clean_desc[:2000]}")  # Ограничение длины
    
    # Атрибуты
    if attrs := product.get("attributes"):
        if isinstance(attrs, list) and attrs:
            parts.append(f"Характеристики: {'; '.join(str(a) for a in attrs[:10])}")
    
    # Продавец
    if seller := product.get("seller", "").strip():
        parts.append(f"Продавец: {seller}")
    
    # Рейтинг
    if rating := product.get("rating"):
        if rating > 0:
            parts.append(f"Рейтинг: {rating}")
    
    return " | ".join(parts)


async def upsert_product(
    client: httpx.AsyncClient,
    base_url: str,
    product: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> tuple[int, bool, str | None]:
    """
    Отправляет один продукт на сервер.
    
    Returns:
        (product_id, success, error_message)
    """
    product_id = product.get("id")
    if not product_id:
        return 0, False, "Missing 'id' field"
    
    text = format_product_text(product)
    if not text:
        return product_id, False, "Empty text after formatting"
    
    async with semaphore:
        try:
            response = await client.post(
                f"{base_url}/upsert",
                json={"id": product_id, "text": text},
                timeout=30.0,
            )
            response.raise_for_status()
            return product_id, True, None
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail.get('detail', '')}"
            except Exception:
                pass
            return product_id, False, error_msg
        except Exception as e:
            return product_id, False, str(e)


async def load_jsonl_file(
    file_path: Path,
    base_url: str,
    batch_size: int = 100,
    max_workers: int = 10,
) -> dict[str, int]:
    """
    Загружает JSONL файл в БД через API.
    
    Returns:
        Статистика: {"total": N, "success": N, "failed": N}
    """
    # Читаем файл
    print(f"📖 Читаем файл: {file_path}")
    products = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)
                products.append(product)
            except json.JSONDecodeError as e:
                print(f"⚠️  Строка {line_num}: ошибка парсинга JSON - {e}")
    
    total = len(products)
    print(f"✅ Прочитано {total} записей\n")
    
    if total == 0:
        return {"total": 0, "success": 0, "failed": 0}
    
    # Проверяем доступность сервера
    print(f"🔍 Проверяем доступность сервера: {base_url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/", timeout=5.0)
            response.raise_for_status()
            print("✅ Сервер доступен\n")
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        print("Убедитесь, что сервис запущен!")
        return {"total": total, "success": 0, "failed": total}
    
    # Загружаем данные
    print(f"🚀 Начинаем загрузку с параметрами:")
    print(f"   Записей: {total}")
    print(f"   Воркеров: {max_workers}")
    print(f"   Размер батча: {batch_size}\n")
    
    stats = {"total": total, "success": 0, "failed": 0}
    failed_ids = []
    
    semaphore = asyncio.Semaphore(max_workers)
    
    async with httpx.AsyncClient() as client:
        # Обрабатываем батчами для контроля памяти
        for i in range(0, total, batch_size):
            batch = products[i:i + batch_size]
            
            tasks = [
                upsert_product(client, base_url, product, semaphore)
                for product in batch
            ]
            
            # Выполняем с progress bar
            results = await tqdm.gather(
                *tasks,
                desc=f"Батч {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}",
                total=len(tasks),
            )
            
            for product_id, success, error in results:
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    failed_ids.append((product_id, error))
    
    # Итоговая статистика
    print(f"\n{'='*60}")
    print(f"📊 РЕЗУЛЬТАТЫ:")
    print(f"   Всего:    {stats['total']}")
    print(f"   Успешно:  {stats['success']} ✅")
    print(f"   Ошибок:   {stats['failed']} ❌")
    print(f"{'='*60}")
    
    if failed_ids:
        print(f"\n⚠️  Не удалось загрузить {len(failed_ids)} записей:")
        for product_id, error in failed_ids[:10]:  # Показываем первые 10
            print(f"   ID {product_id}: {error}")
        if len(failed_ids) > 10:
            print(f"   ... и еще {len(failed_ids) - 10} записей")
    
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Загрузка данных из JSONL в векторную БД через API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Путь к JSONL файлу",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="URL сервиса (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Размер батча для обработки (default: 100)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Количество параллельных воркеров (default: 10)",
    )
    
    args = parser.parse_args()
    
    # Проверки
    if not args.file.exists():
        print(f"❌ Файл не найден: {args.file}")
        return 1
    
    if not args.file.suffix == ".jsonl":
        print(f"⚠️  Предупреждение: файл не имеет расширения .jsonl")
    
    # Запускаем загрузку
    stats = asyncio.run(
        load_jsonl_file(
            args.file,
            args.url,
            args.batch_size,
            args.workers,
        )
    )
    
    # Exit code: 0 если все успешно, 1 если были ошибки
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

