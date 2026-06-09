"""
Обработчики аутентификации: регистрация, вход и выход.
"""
import psycopg2
from aiohttp import web
from app_db import hash_password, run_execute, run_fetchrow

auth_routes = web.RouteTableDef()


@auth_routes.post("/api/register")
async def register_handler(request: web.Request):
    """
    Регистрирует нового пользователя в системе.
    
    Body JSON:
        - name: Имя пользователя
        - email: Email для входа
        - password: Пароль (будет захеширован)
    """
    try:
        data = await request.json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        
        if not name or not email or not password:
            return web.json_response({"error": "Заполните все поля"}, status=400)
            
        password_hash = hash_password(password)
        
        try:
            await run_execute(
                request.app,
                "INSERT INTO users (name, email, password_hash, role_id) VALUES (%s, %s, %s, 1)",
                name, email, password_hash
            )
            return web.json_response({"success": True}, status=200)
        except psycopg2.IntegrityError:
            return web.json_response({"error": "Пользователь с таким Email уже существует"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@auth_routes.post("/api/login")
async def login_handler(request: web.Request):
    """
    Аутентифицирует пользователя и возвращает его данные при успешном входе.
    
    Устанавливает HttpOnly cookie с user_id для отслеживания сессии.
    
    Body JSON:
        - email: Email пользователя
        - password: Пароль
    """
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return web.json_response({"error": "Заполните все поля"}, status=400)
            
        password_hash = hash_password(password)
        
        user = await run_fetchrow(
            request.app,
            """SELECT users.id, users.name, users.email, roles.name as role 
               FROM users 
               JOIN roles ON users.role_id = roles.id 
               WHERE email = %s AND password_hash = %s""",
            email, password_hash
        )

        if not user:
            # 401 - отсутствие авторизации
            return web.json_response({"error": "Неверный логин или пароль"}, status=401)

        # создаем ответ и устанавливаем cookie с id пользователя
        resp = web.json_response({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }, status=200)

        # HttpOnly cookie с user_id
        resp.set_cookie(
            name="user_id",
            value=str(user["id"]),
            httponly=True, # недоступны из JS
            secure=False,
            samesite='Lax', # базовая защита от CSRF
            max_age=7*24*3600 # время жизни - 7 дней
        )

        return resp

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@auth_routes.post("/api/logout")
async def logout_handler(request: web.Request):
    """Очищает cookie авторизации пользователя."""
    try:
        resp = web.json_response({"success": True}, status=200)
        resp.del_cookie('user_id')
        return resp
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
