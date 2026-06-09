"""
Health check обработчик.
"""
from aiohttp import web

health_routes = web.RouteTableDef()


@health_routes.get("/health")
async def healthy(request: web.Request):
    """Проверяет статус работы сервера."""
    return web.Response(text="Сервер работает")
