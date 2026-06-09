"""
Главное приложение: инициализация и запуск сервера aiohttp.
"""
from aiohttp import web
import aiohttp_cors

from app_db import init_db, close_db
from model import load_local_model

# Импортируем все маршруты из обработчиков
from handlers.health import health_routes
from handlers.auth import auth_routes
from handlers.feedback import feedback_routes
from handlers.predictions import prediction_routes
from handlers.history import history_routes


async def make_app():
    """
    Создаёт и конфигурирует приложение aiohttp с CORS, маршрутами и БД.
    
    - Загружает ML модель
    - Инициализирует БД при старте
    - Регистрирует все маршруты из handlers
    - Настраивает CORS для всех маршрутов
    """
    # размер запроса (10МБ)
    app = web.Application(client_max_size=1024**2*10)
    
    load_local_model()
    
    # регистрируем функции при старте и завершении сервера
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    
    # добавляем все маршруты из разных обработчиков
    app.add_routes(health_routes)
    app.add_routes(auth_routes)
    app.add_routes(feedback_routes)
    app.add_routes(prediction_routes)
    app.add_routes(history_routes)
    
    # настраиваем CORS для всех маршрутов
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,  # Разрешить отправку cookies и авторизации
            expose_headers="*",      # Позволить клиенту видеть все заголовки ответа
            allow_headers="*"        # Позволить клиенту отправлять любые заголовки
        )
    })
    
    # применяем CORS ко всем маршрутам
    for route in list(app.router.routes()): 
        cors.add(route)
    
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host='0.0.0.0', port=5111)
