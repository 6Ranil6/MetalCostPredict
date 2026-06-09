#!/usr/bin/env python3
"""
Скрипт для проверки подключения к Ollama из backend контейнера.
Используйте: python test_ollama_connection.py
"""

import asyncio
import os
from ollama import AsyncClient
import aiohttp

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


async def test_ollama_connection():
    """Тестирует подключение к Ollama API."""
    print(f"🔍 Проверка подключения к Ollama: {OLLAMA_URL}")
    print("-" * 60)

    # Тест 1: Проверка через HTTP
    print("\n1️⃣  Проверка доступности API через HTTP...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Ollama API доступен! Статус: {resp.status}")
                    print(f"   Загруженные модели: {len(data.get('models', []))}")
                    for model in data.get("models", []):
                        print(f"   - {model.get('name')}")
                else:
                    print(f"❌ Ошибка HTTP: {resp.status}")
    except asyncio.TimeoutError:
        print("❌ Timeout: Ollama не отвечает в течение 10 секунд")
    except Exception as e:
        print(f"❌ Ошибка подключения: {str(e)}")

    # Тест 2: Проверка через Ollama AsyncClient
    print("\n2️⃣  Проверка подключения через Ollama AsyncClient...")
    try:
        client = AsyncClient(host=OLLAMA_URL)

        # Пытаемся получить список моделей
        models = await asyncio.wait_for(client.list(), timeout=10.0)
        print(f"✅ AsyncClient подключился успешно!")
        print(f"   Доступные модели: {len(models.get('models', []))}")
        for model in models.get("models", []):
            print(f"   - {model.get('name')}")
    except asyncio.TimeoutError:
        print("❌ Timeout: AsyncClient timeout")
    except Exception as e:
        print(f"❌ Ошибка AsyncClient: {str(e)}")

    # Тест 3: Проверка простого запроса к модели
    print("\n3️⃣  Проверка простого запроса к модели...")
    try:
        client = AsyncClient(host=OLLAMA_URL)

        response = await asyncio.wait_for(
            client.chat(
                model="qwen2.5:7b",
                messages=[
                    {
                        "role": "user",
                        "content": "Привет! Ответь одним словом: OK",
                    }
                ],
                stream=False,
                options={"num_ctx": 512},
            ),
            timeout=30.0,
        )
        print(f"✅ Запрос к модели выполнен успешно!")
        print(f"   Ответ: {response.message.content[:100]}...")
    except asyncio.TimeoutError:
        print("❌ Timeout: Запрос к модели занял слишком много времени")
    except Exception as e:
        print(f"❌ Ошибка запроса: {str(e)}")

    print("\n" + "=" * 60)
    print("🏁 Диагностика завершена")


if __name__ == "__main__":
    print("=" * 60)
    print("📋 ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К OLLAMA")
    print("=" * 60)
    asyncio.run(test_ollama_connection())
