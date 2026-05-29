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
    hash_password, run_fetchall_predictions_history,
    run_hide_prediction, run_hide_all_predictions
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
    """Загружает обученную модель CatBoost с диска."""
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
    """Проверяет и приводит данные к необходимому формату для модели."""
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
    """Получает предсказание цены от модели для переданных данных."""
    df_input = df[IMPORTANT_FEATURES]
    prediction = model.predict(df_input)
    return np.expm1(np.atleast_1d(prediction))

routes = web.RouteTableDef()

@routes.get("/health")
async def healthy(request: web.Request):
    """Проверяет статус работы сервера."""
    return web.Response(text="Сервер работает")

@routes.post("/api/register")
async def register_handler(request: web.Request):
    """Регистрирует нового пользователя в системе."""
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
    """Аутентифицирует пользователя и возвращает его данные при успешном входе."""
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
    """Сохраняет сообщение обратной связи от пользователя в БД."""
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
    """Обрабатывает ручной ввод данных и возвращает предсказанную цену."""
    try:
        data = await request.json()
        user_id = data.pop('user_id', None)
        
        df = pd.DataFrame([data])
        if await check_data_format(df):
            prices = get_model_predict(df)
            price = round(float(prices[0]), 2)
            
            # преобразуем значения в JSON
            input_data_clean = {}
            for key, value in data.items():
                if pd.isna(value) or value is None or value == '':
                    input_data_clean[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    input_data_clean[key] = float(value) if isinstance(value, np.floating) else int(value)
                else:
                    input_data_clean[key] = str(value) if value is not None else None
            
            await run_execute(
                request.app,
                "INSERT INTO predictions_history (user_id, input_data, predicted_price) VALUES (%s, %s, %s)",
                user_id, json.dumps(input_data_clean, ensure_ascii=False), price
            )
            
            return web.json_response({"price": price}, status=200)
        return web.json_response({"error": "Invalid format"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.post("/predict-file")
async def file_handler(request: web.Request):
    """Обрабатывает загруженный файл (CSV/Parquet) и возвращает результаты с предсказаниями."""
    try:
        data = await request.post()
        file_field = data.get('file')
        user_id = data.get('user_id')
        
        if not file_field: 
            return web.json_response({"error": "No file"}, status=400)
            
        content = file_field.file.read()
        filename = file_field.filename.lower()
        
        if filename.endswith('.parquet'):
            df_orig = pd.read_parquet(io.BytesIO(content))
        else:
            df_orig = pd.read_csv(io.BytesIO(content), sep=None, engine='python')
        
        # удаляем колонки "Unnamed" (индексы из исходного CSV)
        df_orig = df_orig.loc[:, ~df_orig.columns.str.contains('^Unnamed')]
        
        df_predict = df_orig.copy()
        if await check_data_format(df_predict):
            prices = get_model_predict(df_predict)
            df_orig['Предсказанная_Цена'] = np.round(prices.flatten(), 2)
            
            # сохранение каждой строки в БД если пользователь авторизован
            if user_id:
                for idx, row in df_orig.iterrows():
                    input_data = row.drop('Предсказанная_Цена').to_dict()
                    
                    # преобразуем значения в JSON-совместимые
                    input_data_clean = {}
                    for key, value in input_data.items():
                        if pd.isna(value):
                            input_data_clean[key] = None
                        elif isinstance(value, (np.integer, np.floating)):
                            input_data_clean[key] = float(value) if isinstance(value, np.floating) else int(value)
                        else:
                            input_data_clean[key] = str(value) if value is not None else None
                    
                    predicted_price = row['Предсказанная_Цена']
                    await run_execute(
                        request.app,
                        "INSERT INTO predictions_history (user_id, input_data, predicted_price) VALUES (%s, %s, %s)",
                        user_id, json.dumps(input_data_clean, ensure_ascii=False), predicted_price
                    )
            
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


@routes.get("/api/predictions-history/{user_id}")
async def get_predictions_history(request: web.Request):
    """Возвращает историю предсказаний пользователя."""
    try:
        user_id = request.match_info['user_id']
        
        # историю запросов возвращаем (по умолчанию 50)
        limit = request.query.get('limit', 50)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 1
        except ValueError:
            limit = 50
        
        # получение истории из БД
        records = await run_fetchall_predictions_history(request.app, user_id, limit)
        
        if not records:
            return web.json_response({"history": []}, status=200)
        
        # преобразование результатов
        history = []
        for record in records:
            history.append({
                'id': record['id'],
                'input_data': json.loads(record['input_data']),
                'predicted_price': float(record['predicted_price']),
                'created_at': record['created_at'].isoformat()
            })
        
        return web.json_response({"history": history}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/hide-prediction/{prediction_id}/{user_id}")
async def hide_prediction(request: web.Request):
    """Скрывает отдельное предсказание пользователя из истории (soft delete)."""
    try:
        prediction_id = request.match_info['prediction_id']
        user_id = request.match_info['user_id']
        
        try:
            prediction_id = int(prediction_id)
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID format"}, status=400)
        
        success = await run_hide_prediction(request.app, prediction_id, user_id)
        
        if success:
            return web.json_response({"success": True}, status=200)
        else:
            return web.json_response({"error": "Record not found"}, status=404)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/hide-all-predictions/{user_id}")
async def hide_all_predictions(request: web.Request):
    """Скрывает все предсказания пользователя из истории (soft delete)."""
    try:
        user_id = request.match_info['user_id']
        
        try:
            user_id = int(user_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID format"}, status=400)
        
        count = await run_hide_all_predictions(request.app, user_id)
        
        return web.json_response({"success": True, "hidden_count": count}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def make_app():
    """Создаёт и конфигурирует приложение aiohttp с CORS, маршрутами и БД."""
    app = web.Application(client_max_size=1024**2*50)
    load_local_model()
    
    # регестрация функции при старте/выключении сервера
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    
    app.add_routes(routes)

    # c каких источников принимаем запросы
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,  # разрешить отправку cookies и авторизации
            expose_headers="*", #  позволить клиенту видеть все заголовки ответа
            allow_headers="*" # позволить клиенту отправлять любые заголовки
        )
    })

    for route in list(app.router.routes()): 
        cors.add(route)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host='0.0.0.0', port=5111)
