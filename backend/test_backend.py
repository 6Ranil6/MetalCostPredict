import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

import app
from app_db import hash_password

def test_hash_password():
    """
    Проверяет, что функция хеширования генерирует корректную SHA-256 строку
    длиной 64 символа и выдает верное значение для известного пароля.
    """
    password = "my_secure_password"
    hashed = hash_password(password)
    
    assert len(hashed) == 64
    
    expected_hash = "2c9a8d02fc17ae77e926d38fe83c3529d6638d1d636379503f0c6400e063445f"
    assert hashed == expected_hash


@pytest.mark.asyncio
async def test_check_data_format_valid_inputs():
    """
    Проверяет успешное прохождение валидации для корректных данных.
    Строковые числовые значения должны преобразоваться в типы float,
    а недостающие категориальные колонки - заполниться значением 'отсутствует'.
    """
    test_data = {
        'Наименование': 'Арматура',
        'Размер_A': '12.5',     # число в виде строки
        'Толщина': '6',         # целое число в виде строки
        'Категория_цены': 'Опт'
    }
    df = pd.DataFrame([test_data])
    
    success = await app.check_data_format(df)
    
    assert success is True
    assert df['Размер_A'].iloc[0] == 12.5
    assert df['Толщина'].iloc[0] == 6.0
    assert df['Основная_марка'].iloc[0] == 'отсутствует'


@pytest.mark.asyncio
async def test_check_data_format_invalid_numeric():
    """
    Проверяет поведение валидатора при некорректных входных типах в числовых колонках.
    Неконвертируемый текст должен преобразоваться в NaN, пустые категории - в 'отсутствует'.
    """
    test_data = {
        'Размер_A': 'не_число', # ошибка конвертации
        'Тип_материала': None,   # отсутствующее значение
        'Толщина': '0'          # ноль должен замениться на NaN по вашей логике
    }
    df = pd.DataFrame([test_data])
    
    success = await app.check_data_format(df)
    
    assert success is True
    assert np.isnan(df['Размер_A'].iloc[0])
    assert np.isnan(df['Толщина'].iloc[0])
    assert df['Тип_материала'].iloc[0] == 'отсутствует'



def test_get_model_predict_with_mock(monkeypatch):
    """
    Проверяет вычисление предсказания модели. Физический файл CatBoost заменяется заглушкой.
    Проверяет, что логарифмированное предсказание корректно преобразуется функцией expm1.
    """
    mock_catboost = MagicMock()
    
    mock_catboost.predict.return_value = np.array([4.61512])
    
    # подменяем глобальный объект модели в модуле app на нашу заглушку
    monkeypatch.setattr(app, "model", mock_catboost)
    
    df = pd.DataFrame([dict.fromkeys(app.IMPORTANT_FEATURES, 'отсутствует')])
    
    result = app.get_model_predict(df)
    
    mock_catboost.predict.assert_called_once()
    assert np.isclose(result[0], 100.0, atol=1e-3)
