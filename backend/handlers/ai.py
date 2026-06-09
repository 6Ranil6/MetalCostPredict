"""
Обработчики для AI помощника CPM: общение, обработка изображений и история.
"""

import asyncio
import json
import base64
import os
import logging
from typing import List, Dict, Any
from aiohttp import web
from ollama import AsyncClient

from app_db import run_execute, run_fetchall_ai_chat_history
from data_validation import clean_input_data_for_json

# Настраиваем логирование для диагностики
logger = logging.getLogger(__name__)

ai_routes = web.RouteTableDef()

# Инициализируем Ollama клиент с переменной окружения
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
ollama_client = AsyncClient(host=OLLAMA_URL)

# Переменная для отслеживания статуса Ollama
ollama_status = {
    "available": False,
    "last_check": None,
    "error": None,
}

# Системный промпт для AI помощника
SYSTEM_PROMPT = """Ты — CPM AI, ассистент системы оценки стоимости металлопродукции.

ТВОИ ЗАДАЧИ:
1. Помогать пользователям использовать калькулятор стоимости металлопродукции
2. Отвечать на вопросы о параметрах товара и как их указывать
3. Объяснять значение различных категорий цен (р./т, р./пог.м, р./шт., р./кг, р./м²)
4. Анализировать загруженные изображения с таблицами металлопродукции и извлекать из них данные
5. Когда пользователь загружает изображение с таблицей, тщательно прочитай данные и предложи их

ВАЖНО:
- НЕ раскрывай внутреннюю реализацию системы (архитектуру БД, детали ML модели, источники данных)
- Ведись дружелюбно и помогай пользователям разобраться с функциональностью
- Если на изображении видна таблица с параметрами металлопродукции, извлеки структурированные данные
- Не фантазируй о данных, если не можешь ясно прочитать изображение
- Все ответы давай на русском языке
- Будь краток и информативен"""


async def check_ollama_health() -> bool:
    """Проверяет доступность Ollama API."""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    ollama_status["available"] = True
                    ollama_status["error"] = None
                    logger.info("✓ Ollama API доступен")
                    return True
    except Exception as e:
        ollama_status["available"] = False
        ollama_status["error"] = str(e)
        logger.error(f"✗ Ollama API недоступен: {str(e)}")

    return False


class AIAssistant:
    def __init__(
        self, model_name: str = "qwen2.5:7b", vision_model: str = "qwen3-vl:2b"
    ):
        self.llm_model = model_name
        self.vision_model = vision_model
        self.context_size = 10  # последние 10 сообщений в контексте

    async def _prepare_context(
        self, conversation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Подготавливает контекст для модели из истории (последние N сообщений)."""
        context = [{"role": "system", "content": SYSTEM_PROMPT}]

        # берём последние сообщения для контекста
        recent_messages = (
            conversation_history[-self.context_size :] if conversation_history else []
        )
        for msg in recent_messages:
            context.append({"role": msg["role"], "content": msg["content"]})

        return context

    async def _process_image(self, image_data: str) -> Dict[str, Any]:
        """
        Анализирует изображение с помощью VLM (qwen3-vl или moondream).
        Возвращает структурированные данные о металлопродукции если найдены.
        """
        try:
            # проверяем валидность base64
            if not image_data.startswith("data:image"):
                # если просто base64 без префикса
                image_b64 = image_data
            else:
                # извлекаем base64 часть из data URL
                image_b64 = (
                    image_data.split(",")[1] if "," in image_data else image_data
                )

            # используем qwen3-vl для анализа с timeout в 60 секунд
            response = await asyncio.wait_for(
                ollama_client.chat(
                    model=self.vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": """Проанализируй это изображение. Если на нём видна таблица с характеристиками металлопродукции, 
                        извлеки следующие данные в формате JSON:
                        - Наименование (название товара)
                        - Размер_A (основной размер в мм)
                        - Размер_B (дополнительный размер если есть)
                        - Размер_C (третий размер если есть)
                        - Марка (марка профиля если есть)
                        - Основная_марка (марка стали/материала)
                        - Толщина (в мм)
                        - Категория_цены (р./т, р./пог.м, р./шт., р./кг, р./м²)
                        - Цена (если видна)
                        
                        Ответь ТОЛЬКО валидным JSON без комментариев, даже если некоторые поля пусты.
                        Пример: {"Наименование": "Двутавр 20Б1", "Размер_A": 20.0, ...}
                        
                        Если на изображении нет таблицы с металлопродукцией, верни JSON: {"error": "Таблица не найдена"}""",
                            "images": [image_b64],
                        }
                    ],
                    stream=False,
                    options={"temperature": 0},
                ),
                timeout=60.0,
            )

            # парсим ответ
            content = response.message.content
            try:
                # пробуем найти JSON в ответе
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    return {"success": True, "data": data, "source": "image_analysis"}
            except json.JSONDecodeError:
                pass

            return {
                "success": True,
                "data": None,
                "message": "На изображении не найдена таблица с данными о металлопродукции",
                "source": "image_analysis",
            }

        except Exception as e:
            error_str = str(e).lower()

            # проверяем, есть ли ошибки llama-server или timeout
            if (
                "killed" in error_str
                or "llama" in error_str
                or "timeout" in error_str
                or "connection" in error_str
            ):
                error_msg = "AI помощник временно недоступен при обработке изображения. Пожалуйста, попробуйте позже."
            else:
                error_msg = f"Ошибка при анализе изображения: {str(e)}"

            return {
                "success": False,
                "error": error_msg,
                "source": "image_analysis",
            }

    async def chat(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_id: int = None,
        image_data: str = None,
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение пользователя и возвращает ответ AI.
        Если передано изображение, анализирует его.
        """
        try:
            # если передано изображение, анализируем его первым
            image_analysis = None
            if image_data:
                image_analysis = await self._process_image(image_data)

                # если из изображения извлекли данные, добавляем в сообщение
                if image_analysis.get("success") and image_analysis.get("data"):
                    extracted_data = image_analysis.get("data")
                    if "error" not in extracted_data:
                        user_message = f"""{user_message}

[Данные извлечены из изображения]
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

Пожалуйста, помоги мне использовать эти данные для расчёта цены."""

            # подготавливаем контекст с историей
            context = await self._prepare_context(conversation_history)
            context.append({"role": "user", "content": user_message})

            # получаем ответ от LLM с timeout в 120 секунд
            # Оптимизированные параметры для снижения потребления памяти
            response = await asyncio.wait_for(
                ollama_client.chat(
                    model=self.llm_model,
                    messages=context,
                    stream=False,
                    options={
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_ctx": 2048,  # Уменьшен размер контекста (было 4096)
                        "num_batch": 256,  # Батч размер для оптимизации памяти
                        "num_keep": 24,  # Сохраняем только необходимые токены
                    },
                ),
                timeout=120.0,
            )

            ai_response = response.message.content

            return {
                "success": True,
                "response": ai_response,
                "image_analysis": image_analysis,
            }

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Ошибка при обработке сообщения AI: {str(e)}")

            # проверяем, есть ли ошибки llama-server
            if (
                "killed" in error_str
                or "llama" in error_str
                or "connection" in error_str
                or "timeout" in error_str
            ):
                error_msg = "AI помощник временно недоступен. Пожалуйста, убедитесь, что Ollama сервис запущен, и попробуйте позже."
            else:
                error_msg = f"Ошибка при обработке запроса: {str(e)}"

            return {
                "success": False,
                "error": error_msg,
            }


ai_assistant = AIAssistant(model_name="qwen2.5:7b", vision_model="qwen3-vl:2b")


@ai_routes.get("/api/ai-health")
async def ai_health_handler(request: web.Request):
    """
    Проверяет доступность AI помощника и статус Ollama.
    """
    is_healthy = await check_ollama_health()

    return web.json_response(
        {
            "status": "healthy" if is_healthy else "unavailable",
            "ollama_url": OLLAMA_URL,
            "ollama_available": is_healthy,
            "error": ollama_status.get("error"),
        },
        status=200 if is_healthy else 503,
    )


@ai_routes.post("/api/ai-chat")
async def ai_chat_handler(request: web.Request):
    """
    Обрабатывает сообщение пользователя в чате с AI помощником.

    Body JSON:
        - user_id: ID пользователя (опционально)
        - message: Текстовое сообщение
        - image: Base64 изображение (опционально)
        - session_id: ID сессии чата для контекста

    Returns:
        JSON с ответом AI и ID сообщения
    """
    try:
        # Проверяем доступность Ollama перед обработкой запроса
        if not await check_ollama_health():
            logger.warning("Запрос AI чата, но Ollama недоступен")
            return web.json_response(
                {
                    "error": "AI помощник временно недоступен. Ollama сервис не отвечает. Пожалуйста, попробуйте позже.",
                    "status": "ollama_unavailable",
                },
                status=503,
            )
        data = await request.json()
        user_message = data.get("message", "").strip()
        user_id = data.get("user_id")
        image_data = data.get("image")
        session_id = data.get("session_id")

        if not user_message and not image_data:
            return web.json_response(
                {"error": "Сообщение или изображение не может быть пусто"}, status=400
            )

        # если user_id не в теле, пытаемся взять из cookie
        if not user_id:
            cookie_uid = request.cookies.get("user_id")
            if cookie_uid:
                try:
                    user_id = int(cookie_uid)
                except ValueError:
                    user_id = None

        # получаем историю чата для контекста
        conversation_history = []
        if user_id and session_id:
            records = await run_fetchall_ai_chat_history(
                request.app, user_id, session_id, limit=10
            )
            for record in records:
                conversation_history.append(
                    {"role": record["role"], "content": record["content"]}
                )

        # получаем ответ от AI
        ai_result = await ai_assistant.chat(
            user_message, conversation_history, user_id, image_data
        )

        if not ai_result.get("success"):
            return web.json_response(
                {"error": ai_result.get("error", "Unknown error")}, status=500
            )

        ai_response = ai_result.get("response")

        # сохраняем сообщение пользователя и ответ в БД если user_id есть
        if user_id:
            # сохраняем сообщение пользователя
            await run_execute(
                request.app,
                """INSERT INTO ai_chat_history 
                   (user_id, session_id, role, content, image_included) 
                   VALUES (%s, %s, %s, %s, %s)""",
                user_id,
                session_id or None,
                "user",
                user_message,
                bool(image_data),
            )

            # сохраняем ответ AI
            await run_execute(
                request.app,
                """INSERT INTO ai_chat_history 
                   (user_id, session_id, role, content, image_included) 
                   VALUES (%s, %s, %s, %s, %s)""",
                user_id,
                session_id or None,
                "assistant",
                ai_response,
                False,
            )

        return web.json_response(
            {
                "success": True,
                "response": ai_response,
                "image_analysis": ai_result.get("image_analysis"),
            },
            status=200,
        )

    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Ошибка в обработчике ai_chat_handler: {str(e)}", exc_info=True)

        # проверяем, есть ли ошибки llama-server
        if (
            "killed" in error_str
            or "llama" in error_str
            or "timeout" in error_str
            or "connection" in error_str
        ):
            error_msg = "AI помощник временно недоступен. Ollama сервис не отвечает или был перезагружен. Пожалуйста, попробуйте позже."
            status_code = 503
        else:
            error_msg = f"Ошибка сервера: {str(e)}"
            status_code = 500

        return web.json_response({"error": error_msg}, status=status_code)


@ai_routes.get("/api/ai-history/{user_id}")
async def ai_history_handler(request: web.Request):
    """
    Возвращает историю чатов AI пользователя.

    URL parameters:
        - user_id: ID пользователя или 'me'

    Query parameters:
        - limit: Количество сессий (по умолчанию 20)

    Returns:
        JSON со списком сессий и сообщений
    """
    try:
        user_id = request.match_info["user_id"]

        # поддержка 'me' маркера
        if user_id in ("me", "current"):
            cookie_uid = request.cookies.get("user_id")
            if not cookie_uid:
                return web.json_response({"error": "Unauthorized"}, status=401)
            user_id = cookie_uid

        try:
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid user_id"}, status=400)

        limit = request.query.get("limit", 20)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 1
        except ValueError:
            limit = 20

        # получаем все сессии пользователя
        records = await run_fetchall_ai_chat_history(
            request.app, user_id, session_id=None, limit=None
        )

        if not records:
            return web.json_response({"history": []}, status=200)

        # группируем по session_id
        sessions = {}
        for record in records:
            session_id = record["session_id"] or "default"
            if session_id not in sessions:
                sessions[session_id] = {
                    "session_id": session_id,
                    "messages": [],
                    "created_at": None,
                }

            msg = {
                "id": record["id"],
                "role": record["role"],
                "content": record["content"],
                "image_included": record.get("image_included", False),
                "created_at": (
                    record["created_at"].isoformat()
                    if record.get("created_at")
                    else None
                ),
            }
            sessions[session_id]["messages"].append(msg)

            if sessions[session_id]["created_at"] is None:
                sessions[session_id]["created_at"] = msg["created_at"]

        # сортируем по дате последнего сообщения
        sorted_sessions = sorted(
            sessions.values(), key=lambda s: s["created_at"] or "", reverse=True
        )

        return web.json_response({"history": sorted_sessions[:limit]}, status=200)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
