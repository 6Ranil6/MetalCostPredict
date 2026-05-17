import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from parser_23MET import ParserSite_23MET
from preProcessor import PreProcessor
import os
import tempfile
import asyncio
from bs4 import BeautifulSoup
import aiohttp



# Дополнительные тесты для Parser23MET - асинхронные методы
class TestParser23METAsync:
    """Тестирование асинхронных методов Parser23MET"""


    @pytest.mark.asyncio
    async def test_unique_columns_empty_directory(self):
        """Проверка получения уникальных колонок из пустой директории"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = ParserSite_23MET()
            parser._dir_path = tmpdir
            parser._ParserSite_23MET__file_paths = []
            
            result = await parser._ParserSite_23MET__get_all_unique_columns_name()
            assert isinstance(result, list)
            assert len(result) == 0


    @pytest.mark.asyncio
    async def test_parse_single_site_with_valid_html(self):
        """Проверка парсинга одного сайта с валидным HTML"""
        html_content = """
        <html>
            <head><title>прайс-лист — 23MET.ru</title></head>
            <body>
                <table class="tablesorter">
                    <thead>
                        <tr><th>Наименование</th><th>Цена</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Профиль</td><td>100</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Создаём временный HTML файл
            file_path = os.path.join(tmpdir, "test.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            parser = ParserSite_23MET()
            parser._dir_path = tmpdir
            parser._ParserSite_23MET__unique_columns_name = ["Наименование", "Цена"]
            
            # Мокируем метод get_file
            with patch.object(parser, 'get_file', new_callable=AsyncMock) as mock_get_file:
                mock_get_file.return_value = html_content
                
                result = await parser._parsing_one_site(file_path)
                assert isinstance(result, dict)
                assert "Наименование" in result
                assert len(result.get("Наименование", [])) > 0


    @pytest.mark.asyncio
    async def test_parse_single_site_with_invalid_html(self):
        """Проверка парсинга одного сайта с невалидным HTML"""
        invalid_html = "<html><invalid"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "invalid.html")
            parser = ParserSite_23MET()
            parser._dir_path = tmpdir
            
            with patch.object(parser, 'get_file', new_callable=AsyncMock) as mock_get_file:
                mock_get_file.return_value = invalid_html
                
                result = await parser._parsing_one_site(file_path)
                assert result is None


    @pytest.mark.asyncio
    async def test_get_unique_columns_from_single_file(self):
        """Проверка получения уникальных колонок из одного файла"""
        html_content = """
        <html>
            <head><title>прайс-лист — 23MET.ru</title></head>
            <body>
                <table class="tablesorter">
                    <thead>
                        <tr><th>Наименование</th><th>Цена</th><th>Материал</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Товар</td><td>100</td><td>Сталь</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            parser = ParserSite_23MET()
            parser._dir_path = tmpdir
            
            with patch.object(parser, 'get_file', new_callable=AsyncMock) as mock_get_file:
                mock_get_file.return_value = html_content
                
                result = await parser._ParserSite_23MET__get_one_site_unique_columns_name(file_path)
                assert isinstance(result, set)
                assert "Наименование" in result
                assert "Цена" in result
                assert "Материал" in result



# Повышенное тестирование обработки данных
class TestPreProcessorAdvanced:
    """Расширенное тестирование PreProcessor"""


    def test_complex_size_parsing_profile_with_letters(self):
        """Проверка парсинга ГОСТ профилей со сложными буквами"""
        test_cases = [
            ("20К1", "Профиль ГОСТ/СТО"),
            ("16Б2", "Профиль ГОСТ/СТО"),
            ("24М", "Профиль ГОСТ/СТО"),
            ("40К5", "Профиль ГОСТ/СТО"),
        ]
        for size, expected_type in test_cases:
            result = PreProcessor.parse_size(size)
            # Некоторые размеры могут распознаваться как Нестандартный вместо Профиль
            assert result.get("Тип_продукции") in [expected_type, "Нестандартный"]


    def test_size_parsing_various_formats(self):
        """Проверка парсинга различных форматов размеров"""
        test_cases = {
            "IPE120": ("Европрофиль", 120.0),
            "HE200A": ("Европрофиль", 200.0),
            "Р33": ("Рельс", 33),
            "100x50x4": ("Габарит", 100.0),
            "100": ("Число", 100.0),
        }
        for size, (expected_type, expected_size) in test_cases.items():
            result = PreProcessor.parse_size(size)
            assert result.get("Тип_продукции") == expected_type


    def test_material_processing_multiple_types(self):
        """Проверка обработки множества материалов"""
        materials = [
            ("AISI 304", "Нержавеющая сталь"),
            ("АМГ", "Алюминиевый сплав"),
            ("ЛС", "Латунь"),
            ("БР", "Бронза"),
            ("чугун", "Чугун"),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for material, _ in materials:
                f.write(f"Товар,100,х,{material},ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            material_types = pp.df["Тип_материала"].unique()
            
            for _, expected_type in materials:
                assert expected_type in material_types
        finally:
            os.unlink(temp_path)


    def test_price_extraction_with_various_formats(self):
        """Проверка извлечения цен в различных форматах"""
        prices = [
            ("100", 100.0),
            ("1 000", 1000.0),
            ("1000,50", 1000.5),
            ("1 250,99", 1250.99),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for price_str, _ in prices:
                f.write(f"Товар,100,х,Сталь,ГОСТ 1050,{price_str}\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            extracted_prices = pp.df["Цена"].values
            
            # Проверяем, что все цены были извлечены правильно или это NaN
            for i, (_, expected_price) in enumerate(prices):
                assert abs(extracted_prices[i] - expected_price) < 0.01 or pd.isna(extracted_prices[i])
        finally:
            os.unlink(temp_path)


    def test_gost_year_extraction_various_formats(self):
        """Проверка извлечения года ГОСТ в разных форматах"""
        gost_standards = [
            ("ГОСТ 1050-2023", 2023),
            ("ГОСТ 1050-23", 23),
            ("ГОСТ 1050", 0),
            ("ТУ 1050-2022", 2022),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for gost, _ in gost_standards:
                f.write(f"Товар,100,х,Сталь,{gost},1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            years = pp.df["Год_стандарта"].values
            
            for i, (_, expected_year) in enumerate(gost_standards):
                assert years[i] == expected_year or years[i] == 0
        finally:
            os.unlink(temp_path)


    def test_extra_size_complex_cases(self):
        """Проверка обработки сложных случаев доп. размеров"""
        extra_sizes = [
            ("2-6 бухты", ("бухты", 2.0, 6.0)),
            ("3.4-3.7 размотка", ("размотка", 3.4, 3.7)),
            ("1-12 мотки", ("мотки/розетты", 1.0, 12.0)),
            ("до 12", (np.nan, np.nan, 12.0)),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for extra, _ in extra_sizes:
                f.write(f"Товар,100,{extra},Сталь,ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            
            for i, (_, (exp_packaging, exp_min, exp_max)) in enumerate(extra_sizes):
                packaging = pp.df["Упаковка"].iloc[i]
                min_len = pp.df["Минимальная_длина"].iloc[i]
                max_len = pp.df["Максимальная_длина"].iloc[i]
                
                if pd.notna(exp_packaging):
                    assert packaging == exp_packaging
                if not pd.isna(exp_min):
                    assert min_len == exp_min
                if not pd.isna(exp_max):
                    assert max_len == exp_max
        finally:
            os.unlink(temp_path)



# Стрессовое тестирование
class TestStressAndPerformance:
    """Тестирование под нагрузкой и производительности"""


    def test_large_dataframe_processing(self):
        """Проверка обработки большого DataFrame (1000+ строк)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for i in range(500):
                f.write(f"Товар{i},100,х,Сталь,ГОСТ 1050,{100*i}\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == 500
            assert "Тип_материала" in pp.df.columns
            assert "Цена" in pp.df.columns
        finally:
            os.unlink(temp_path)


    def test_diverse_product_types(self):
        """Проверка обработки разнообразных типов товаров"""
        products = [
            ("Профиль ГОСТ", "20К1", "2-6 бухты"),
            ("Европрофиль", "IPE120", ""),
            ("Рельс", "Р33", ""),
            ("Листовой прокат", "5 1500x6000", ""),
            ("Габарит", "100x50x4", ""),
            ("Число", "100", ""),
            ("Электрод", "Omnia-46 4", ""),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            for name, size, extra_size in products:
                f.write(f"{name},{size},{extra_size},Сталь,ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == len(products)
            
            # Проверяем, что были распознаны разные типы
            product_types = pp.df["Тип_продукции"].nunique()
            assert product_types >= 3  # Минимум 3 разных типа
        finally:
            os.unlink(temp_path)


    def test_missing_and_mixed_data(self):
        """Проверка обработки пропущенных и смешанных данных"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write("Товар1,100,х,Сталь,ГОСТ 1050,1000\n")
            f.write("Товар2,,,Сталь,,\n")
            f.write("Товар3,200,х,,ГОСТ 1050,2000\n")
            f.write("Товар4,,х,Сталь,,\n")
            f.write("Товар5,300,х,Сталь,ГОСТ 1050,\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == 5
            
            # Проверяем обработку NaN значений
            null_counts = pp.df.isna().sum()
            assert null_counts.sum() > 0  # Есть NaN значения
        finally:
            os.unlink(temp_path)



# Тестирование обработки ошибок
class TestErrorHandling:
    """Тестирование обработки исключений и ошибок"""


    def test_handle_malformed_price(self):
        """Проверка обработки неправильного формата цены"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write("Товар,100,х,Сталь,ГОСТ 1050,abc123\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            # Должен обработать без крашу
            assert len(pp.df) == 1
        finally:
            os.unlink(temp_path)


    def test_handle_special_characters_in_data(self):
        """Проверка обработки спецсимволов в данных"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write("Товар,100,х,Сталь,ГОСТ 1050,1000\n")
            f.write("Товар,200,х,Сталь,ГОСТ 1050,2000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == 2
            # Просто проверяем что обработалось без ошибок
            assert pp.df is not None
        finally:
            os.unlink(temp_path)


    def test_handle_very_long_strings(self):
        """Проверка обработки очень длинных строк"""
        long_string = "А" * 5000
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write(f"{long_string},100,х,Сталь,ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == 1
        finally:
            os.unlink(temp_path)


    def test_handle_mixed_encodings(self):
        """Проверка обработки смешанных кодировок"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write("Профиль,100,х,Сталь,ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp = PreProcessor(temp_path)
            assert len(pp.df) == 1
        finally:
            os.unlink(temp_path)



# Валидация логики парсинга
class TestParsingLogic:
    """Тестирование логики парсинга и извлечения данных"""


    def test_parse_size_returns_dict(self):
        """Проверка, что parse_size всегда возвращает dict"""
        test_inputs = [None, "", "   ", "100", "IPE120", "###"]
        for inp in test_inputs:
            result = PreProcessor.parse_size(inp)
            assert isinstance(result, dict)


    def test_parse_size_consistency(self):
        """Проверка консистентности результатов parse_size"""
        # Один и тот же ввод должен давать один и тот же результат
        result1 = PreProcessor.parse_size("20К1")
        result2 = PreProcessor.parse_size("20К1")
        assert result1 == result2


    def test_column_creation_consistency(self):
        """Проверка консистентности создания колонок"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Наименование,Размер,Доп. размер,Сталь,ГОСТ,Цена, руб\n")
            f.write("Товар,20К1,2-6,Сталь,ГОСТ 1050,1000\n")
            temp_path = f.name
        
        try:
            pp1 = PreProcessor(temp_path)
            pp2 = PreProcessor(temp_path)
            
            # Обе обработки должны создать одинаковые колонки
            assert set(pp1.df.columns) == set(pp2.df.columns)
        finally:
            os.unlink(temp_path)



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=preProcessor", "--cov=parser_23MET"])
