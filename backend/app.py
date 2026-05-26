import os
import io
import json
import asyncio
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor
from aiohttp import web 
import aiohttp_cors
import psycopg2

from app_db import (
    init_db, close_db, run_execute, run_fetchrow, 
    hash_password
)

IMPORTANT_FEATURES = [
    'Категория_цены', 'Основная_марка', 'Наименование', 'Размер_A', 
    'Тип_материала', 'Размер_B', 'Тип_продукции', 'Размер_C', 
    'Условие_цены', 'Толщина', 'Типоразмер', 'Номер_стандарта', 
    'Тип_стандарта', 'Марка', 'Максимальная_длина'
]

NUMERIC_FEATURES = ['Размер_A', 'Размер_B', 'Размер_C', 'Толщина', 'Типоразмер', 'Максимальная_длина']
CAT_FEATURES = [f for f in IMPORTANT_FEATURES if f not in NUMERIC_FEATURES]

model = CatBoostRegressor()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_local_model():
    paths_to_try = [
        os.path.join(BASE_DIR, "models", "model.cb"),
        os.path.join(BASE_DIR, "modles", "model.cb")
    ]
    
    model_path = None
    for path in paths_to_try:
        if os.path.exists(path):
            model_path = path
            break
            
    if model_path:
        model.load_model(model_path)
        print(f"Модель успешно загружена из: {model_path}")
    else:
        print(f"Ошибка: Файл модели не найден по путям: {paths_to_try}")

async def check_data_format(df: pd.DataFrame):
    try:
        for feat in IMPORTANT_FEATURES:
            if feat not in df.columns: 
                df[feat] = np.nan
        for col in NUMERIC_FEATURES:
            df[col] = pd.to_numeric(df[col], errors='coerce').replace(0, np.nan)
        for col in CAT_FEATURES:
            df[col] = (df[col]
                       .fillna('отсутствует')
                       .astype(str)
                       .str.strip()
                       .replace(['nan', 'None', '', 'NaN'], 'отсутствует'))
        return True
    except Exception as e:
        print(f"Ошибка валидации данных: {e}")
        return False

def get_model_predict(df: pd.DataFrame):
    df_input = df[IMPORTANT_FEATURES]
    prediction = model.predict(df_input)
    return np.expm1(np.atleast_1d(prediction))

routes = web.RouteTableDef()

@routes.get("/health")
async def healthy(request: web.Request):
    return web.Response(text="Сервер работает")

@routes.post("/api/register")
async def register_handler(request: web.Request):
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

@routes.post("/api/login")
async def login_handler(request: web.Request):
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
            
        return web.json_response({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.post("/api/feedback")
async def feedback_handler(request: web.Request):
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


@routes.post("/predict-manual")
async def manual_handler(request: web.Request):
    try:
        data = await request.json()
        user_id = data.pop('user_id', None)
        
        df = pd.DataFrame([data])
        if await check_data_format(df):
            prices = get_model_predict(df)
            price = round(float(prices[0]), 2)
            
            await run_execute(
                request.app,
                "INSERT INTO predictions_history (user_id, input_data, predicted_price) VALUES (%s, %s, %s)",
                user_id, json.dumps(data, ensure_ascii=False), price
            )
            
            return web.json_response({"price": price}, status=200)
        return web.json_response({"error": "Invalid format"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.post("/predict-file")
async def file_handler(request: web.Request):
    try:
        data = await request.post()
        file_field = data.get('file')
        if not file_field: 
            return web.json_response({"error": "No file"}, status=400)
            
        content = file_field.file.read()
        filename = file_field.filename.lower()
        
        if filename.endswith('.parquet'):
            df_orig = pd.read_parquet(io.BytesIO(content))
        else:
            df_orig = pd.read_csv(io.BytesIO(content), sep=None, engine='python')
            
        df_predict = df_orig.copy()
        if await check_data_format(df_predict):
            prices = get_model_predict(df_predict)
            df_orig['Предсказанная_Цена'] = np.round(prices.flatten(), 2)
            
            output = io.StringIO()
            df_orig.to_csv(output, index=False)
            return web.Response(
                body=output.getvalue().encode('utf-8'), 
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="result.csv"'}
            )
        return web.json_response({"error": "Data validation failed"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def make_app():
    app = web.Application(client_max_size=1024**2*50)
    load_local_model()
    
    # регестрация функции при старте/выключении сервера
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    
    app.add_routes(routes)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, 
            expose_headers="*", 
            allow_headers="*"
        )
    })
    for route in list(app.router.routes()): 
        cors.add(route)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host='0.0.0.0', port=5111)
