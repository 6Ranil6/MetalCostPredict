"""
Валидация и подготовка данных для модели предсказания.
"""
import numpy as np
import pandas as pd
from config import IMPORTANT_FEATURES, NUMERIC_FEATURES, CAT_FEATURES


async def check_data_format(df: pd.DataFrame) -> bool:
    """
    Проверяет и приводит данные к необходимому формату для модели.
    
    - Добавляет недостающие признаки как NaN
    - Преобразует числовые значения в соответствующий тип
    - Стандартизирует категориальные значения
    
    Args:
        df: DataFrame для проверки
        
    Returns:
        True если данные валидны, False в случае ошибки
    """
    try:
        # Добавляем отсутствующие признаки
        for feat in IMPORTANT_FEATURES:
            if feat not in df.columns: 
                df[feat] = np.nan
        
        # Обработка числовых признаков
        for col in NUMERIC_FEATURES:
            df[col] = pd.to_numeric(df[col], errors='coerce').replace(0, np.nan)
        
        # Обработка категориальных признаков
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


def clean_input_data_for_json(data: dict) -> dict:
    """
    Преобразует значения данных в JSON-совместимый формат.
    
    Args:
        data: Словарь с входными данными
        
    Returns:
        Очищенный словарь с преобразованными значениями
    """
    input_data_clean = {}
    for key, value in data.items():
        if pd.isna(value) or value is None or value == '':
            input_data_clean[key] = None
        elif isinstance(value, (np.integer, np.floating)):
            input_data_clean[key] = float(value) if isinstance(value, np.floating) else int(value)
        else:
            input_data_clean[key] = str(value) if value is not None else None
    
    return input_data_clean
