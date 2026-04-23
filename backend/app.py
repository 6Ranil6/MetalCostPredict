import os
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor
from aiohttp import web 
import aiohttp_cors
import io

IMPORTANT_FEATURES = [
    'Категория_цены', 'Основная_марка', 'Наименование', 'Размер_A', 
    'Тип_материала', 'Размер_B', 'Тип_продукции', 'Размер_C', 
    'Условие_цены', 'Толщина', 'Типоразмер', 'Номер_стандарта', 
    'Тип_стандарта', 'Марка', 'Максимальная_длина'
]

NUMERIC_FEATURES = ['Размер_A', 'Размер_B', 'Размер_C', 'Толщина', 'Типоразмер', 'Максимальная_длина']
CAT_FEATURES = [f for f in IMPORTANT_FEATURES if f not in NUMERIC_FEATURES]

model = CatBoostRegressor()

def load_local_model():
    model_path = "models/model.cb"
    if os.path.exists(model_path):
        model.load_model(model_path)
    else:
        print(f"Файл {model_path} не найден!")

async def check_data_format(df: pd.DataFrame):
    try:
        for feat in IMPORTANT_FEATURES:
            if feat not in df.columns: df[feat] = np.nan
        for col in NUMERIC_FEATURES:
            df[col] = pd.to_numeric(df[col], errors='coerce').replace(0, np.nan)
        for col in CAT_FEATURES:
            df[col] = df[col].fillna('отсутствует').astype(str).str.strip().replace(['nan', 'None', '', 'NaN'], 'отсутствует')
        return True
    except Exception as e:
        print(f"Ошибка валидации: {e}")
        return False

def get_model_predict(df: pd.DataFrame):
    df_input = df[IMPORTANT_FEATURES]
    prediction = model.predict(df_input)
    return np.expm1(np.atleast_1d(prediction))

routes = web.RouteTableDef()

@routes.get("/health")
async def healthy(request: web.Request):
    return web.Response(text="Сервер работает")

@routes.post("/predict-manual")
async def manual_handler(request: web.Request):
    try:
        data = await request.json()
        df = pd.DataFrame([data])
        if await check_data_format(df):
            prices = get_model_predict(df)
            return web.json_response({"price": round(float(prices[0]), 2)}, status=200)
        return web.json_response({"error": "Invalid format"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@routes.post("/predict-file")
async def file_handler(request: web.Request):
    try:
        data = await request.post()
        file_field = data.get('file')
        if not file_field: return web.json_response({"error": "No file"}, status=400)
        content = file_field.file.read()
        df_orig = pd.read_csv(io.BytesIO(content), sep=None, engine='python')
        df_predict = df_orig.copy()
        if await check_data_format(df_predict):
            prices = get_model_predict(df_predict)
            df_orig['Предсказанная_Цена'] = np.round(prices.flatten(), 2)
            output = io.StringIO()
            df_orig.to_csv(output, index=False)
            return web.Response(body=output.getvalue().encode('utf-8'), content_type='text/csv',
                                headers={'Content-Disposition': 'attachment; filename="result.csv"'})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def make_app():
    app = web.Application(client_max_size=1024**2*50)
    load_local_model()
    app.add_routes(routes)
    cors = aiohttp_cors.setup(app, defaults={"*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")})
    for route in list(app.router.routes()): cors.add(route)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host='0.0.0.0', port=5111)
