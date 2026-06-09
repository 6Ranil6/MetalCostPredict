"""
Управление загрузкой и использованием ML модели CatBoost.
"""
import os
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from config import BASE_DIR, IMPORTANT_FEATURES

# Глобальный экземпляр модели
model = CatBoostRegressor()


def load_local_model():
    """
    Загружает обученную модель CatBoost с диска.
    Пытается найти модель в известных местах.
    """
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


def get_model_predict(df: pd.DataFrame) -> np.ndarray:
    """
    Получает предсказание цены от модели для переданных данных.
    
    Args:
        df: DataFrame с необходимыми признаками
        
    Returns:
        Массив предсказанных цен (inverse log transform)
    """
    df_input = df[IMPORTANT_FEATURES]
    prediction = model.predict(df_input)
    return np.expm1(np.atleast_1d(prediction))
