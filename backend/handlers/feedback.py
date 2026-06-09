"""
Обработчик обратной связи от пользователей.
"""
from aiohttp import web
from app_db import run_execute

feedback_routes = web.RouteTableDef()


@feedback_routes.post("/api/feedback")
async def feedback_handler(request: web.Request):
    """
    Сохраняет сообщение обратной связи от пользователя в БД.
    
    Body JSON:
        - user_id: ID пользователя (опционально)
        - name: Имя отправителя
        - email: Email отправителя
        - subject: Тема сообщения
        - message: Текст сообщения
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        name = data.get("name")
        email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")
        
        if not name or not email or not subject or not message:
            return web.json_response({"error": "Заполните все обязательные поля"}, status=400)
            
        await run_execute(
            request.app,
            "INSERT INTO feedback_messages (user_id, name, email, subject, message) VALUES (%s, %s, %s, %s, %s)",
            user_id, name, email, subject, message
        )
        return web.json_response({"success": True}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
