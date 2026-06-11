"""
Обработчики предсказания цен: ручной ввод и загрузка файлов.
"""
import io
import json
import pandas as pd
import numpy as np
from aiohttp import web

from app_db import run_execute
from config import MAX_FILE_SIZE, IMPORTANT_FEATURES
from model import get_model_predict
from data_validation import check_data_format, clean_input_data_for_json

prediction_routes = web.RouteTableDef()


@prediction_routes.post("/api/predict-manual")
async def manual_handler(request: web.Request):
    """
    Обрабатывает ручной ввод данных и возвращает предсказанную цену.
    
    Body JSON:
        - user_id: ID пользователя (опционально)
        - + все признаки для предсказания (IMPORTANT_FEATURES)
    
    Returns:
        JSON с предсказанной ценой или ошибку
    """
    try:
        data = await request.json()
        user_id = data.pop('user_id', None)

        # если user_id не передали в теле запроса, пытаемся взять из cookie
        if not user_id:
            cookie_uid = request.cookies.get('user_id')
            if cookie_uid:
                try:
                    user_id = int(cookie_uid)
                except ValueError:
                    user_id = None
        
        df = pd.DataFrame([data])
        if await check_data_format(df):
            prices = get_model_predict(df)
            price = round(float(prices[0]), 2)
            
            # преобразуем значения в JSON
            input_data_clean = clean_input_data_for_json(data)
            
            await run_execute(
                request.app,
                "INSERT INTO predictions_history (user_id, input_data, predicted_price) VALUES (%s, %s, %s)",
                user_id, json.dumps(input_data_clean, ensure_ascii=False), price
            )
            
            return web.json_response({"price": price}, status=200)
        return web.json_response({"error": "Invalid format"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@prediction_routes.post("/api/predict-file")
async def file_handler(request: web.Request):
    """
    Обрабатывает загруженный файл (CSV/Parquet) и возвращает результаты с предсказаниями.
    
    Form data:
        - file: CSV или Parquet файл
        - user_id: ID пользователя (опционально)
    
    Returns:
        CSV файл с добавленной колонкой 'Предсказанная_Цена'
    """
    try:
        # Проверка размера через заголовки
        if request.content_length and request.content_length > MAX_FILE_SIZE:
            return web.json_response(
                {"error": "Файл слишком большой. Максимальный размер — 5МБ"}, 
                status=413
            )

        data = await request.post()
        file_field = data.get('file')
        user_id = data.get('user_id')

        # если user_id не передали в форме, пробуем взять из cookie
        if not user_id:
            cookie_uid = request.cookies.get('user_id')
            if cookie_uid:
                try:
                    user_id = int(cookie_uid)
                except ValueError:
                    user_id = None
        
        if not file_field: 
            return web.json_response(
                {"error": "Файл не выбран. Пожалуйста, выберите файл для загрузки."}, 
                status=400
            )
            
        content = file_field.file.read()
        
        if len(content) > MAX_FILE_SIZE:
            return web.json_response(
                {"error": "Файл превышает лимит 5МБ"}, 
                status=413
            )
            
        filename = file_field.filename.lower()
        
        # Проверка на пустой файл
        if not content or len(content) == 0:
            return web.json_response(
                {"error": "Загруженный файл пуст. Пожалуйста, выберите файл с данными."}, 
                status=400
            )
        
        # Попытка прочитать файл
        try:
            if filename.endswith('.parquet'):
                df_orig = pd.read_parquet(io.BytesIO(content))
            elif filename.endswith('.csv'):
                df_orig = pd.read_csv(io.BytesIO(content), sep=None, engine='python')
            else:
                return web.json_response(
                    {"error": f"Неподдерживаемый формат файла '{filename}'. Пожалуйста, используйте CSV или Parquet."}, 
                    status=400
                )
        except pd.errors.EmptyDataError:
            return web.json_response(
                {"error": "Файл пуст или содержит только заголовок. Пожалуйста, добавьте данные в файл."}, 
                status=400
            )
        except Exception as e:
            return web.json_response(
                {"error": f"Ошибка при чтении файла: {str(e)}"}, 
                status=400
            )
        
        if df_orig.empty:
            return web.json_response(
                {"error": "Файл не содержит данных. Пожалуйста, убедитесь, что файл содержит хотя бы одну строку с данными."}, 
                status=400
            )
        
        # Проверка на наличие ОБЯЗАТЕЛЬНОЙ колонки "Категория_цены"
        if 'Категория_цены' not in df_orig.columns:
            return web.json_response(
                {"error": "КРИТИЧЕСКАЯ ОШИБКА: Колонка 'Категория_цены' не найдена в файле. Эта колонка обязательна для обработки. Пожалуйста, добавьте колонку 'Категория_цены' в ваш файл."}, 
                status=400
            )
        
        # Проверка на наличие требуемых колонок
        missing_required_columns = [col for col in IMPORTANT_FEATURES if col not in df_orig.columns]
        if len(missing_required_columns) == len(IMPORTANT_FEATURES):
            return web.json_response(
                {"error": f"Файл не содержит требуемые колонки. Ожидаемые колонки: {', '.join(IMPORTANT_FEATURES)}"}, 
                status=400
            )
        
        # Предупреждение: если отсутствуют некоторые колонки (но не критично)
        if missing_required_columns:
            print(f"Предупреждение: отсутствуют колонки: {missing_required_columns}. Они будут заполнены значением 'отсутствует'.")
        
        # Удаляем колонки "Unnamed" (индексы из исходного CSV)
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
                    input_data_clean = clean_input_data_for_json(input_data)
                    
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
        return web.json_response(
            {"error": "Ошибка валидации данных: не удалось обработать формат данных в файле. Проверьте соответствие структуры файла требованиям."}, 
            status=400
        )
    except Exception as e:
        return web.json_response(
            {"error": f"Ошибка сервера при обработке файла. Пожалуйста, попробуйте позже."}, 
            status=500
        )
