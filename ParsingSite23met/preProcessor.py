import pandas as pd
import numpy as np
import re


class PreProcessor:

    def __init__(self, csv_file_path):
        self.__df = pd.read_csv(csv_file_path, index_col=0, dtype="unicode")
        self.__del_space()
        self.__df = self.__df.replace(
            r"^\s*$", np.nan, regex=True
        )  # Заменяем пустые строки в данных на тип NaN
        self.__preprocessing_size_col()
        self.__preprocessing_extra_size_col()
        self.__process_steel_col()
        self.__process_gost_col()
        self.__union_price_cols()

        self.__df = self.__df.replace(r"^\s*$", np.nan, regex=True)
        del self.__df["Доп. размер"]
        del self.__df["Размер"]
        del self.__df["Материал"]

    @property
    def df(self):
        return self.__df

    def __del_space(self):
        """
        Удаляет ненужные пробелы
        """
        for col in self.__df.columns:
            self.__df[col] = self.__df[col].str.strip()

    def __preprocessing_extra_size_col(self):
        """
        Обрабатывает колонку с доп. размером
        """
        col_name = "Доп. размер"
        df = self.__df

        df[col_name] = df[col_name].astype(str).str.lower().str.strip()
        df[col_name] = df[col_name].replace(
            ["", "nan", "н.д", "нд", "н/д", "с н/д", "с ост."], np.nan
        )

        def extract_all_data(text):
            if pd.isna(text):
                return pd.Series(
                    [np.nan, np.nan, np.nan, np.nan],
                    index=[
                        "Минимальная_длина",
                        "Максимальная_длина",
                        "Упаковка",
                        "Примечание_для_цены",
                    ],
                )

            original_text = text

            packaging = np.nan
            if "бухты" in text:
                packaging = "бухты"
                text = text.replace("бухты", "").strip()
            elif "размотка" in text:
                packaging = "размотка"
                text = text.replace("размотка", "").strip()
            elif "мотки" in text or "розетты" in text:
                packaging = "мотки/розетты"
                text = text.replace("мотки", "").replace("розетты", "").strip()

            length_primary = np.nan
            length_max = np.nan
            notes = text

            # Вариант 1: Диапазон "число-число" (e.g., "2-6", "3.4-3.7")
            range_match = re.search(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", text)
            if range_match:
                vals = sorted(
                    [float(range_match.group(1)), float(range_match.group(2))]
                )
                length_primary, length_max = vals[0], vals[1]
                # Очищаем текст от найденного диапазона для примечаний
                notes = re.sub(r"\d+\.?\d*\s*-\s*\d+\.?\d*", "", text).strip()

            # Вариант 2: Размеры через "х" (e.g., "1.5х10", "1000х1000")
            elif "х" in text:
                # Эти размеры не являются линейными, поэтому оставляем их в примечаниях
                # а поля длин оставляем пустыми.
                notes = original_text

            # Вариант 3: Префикс "до" (e.g., "до 12")
            elif text.startswith("до "):
                numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
                if numbers:
                    length_max = float(numbers[0])
                notes = text

            # Вариант 4: Стандартные числа (одиночные или списки)
            else:
                numbers_str = re.findall(r"\b\d+(?:\.\d+)?\b", text)
                if numbers_str:
                    numeric_values = sorted([float(n) for n in numbers_str])
                    if len(numeric_values) == 1:
                        length_primary = length_max = numeric_values[0]
                    elif len(numeric_values) > 1:
                        length_primary = numeric_values[0]
                        length_max = numeric_values[-1]

                    notes = re.sub(r"[\d\.\s,]+", "", text).strip()

            if not notes or notes.isspace():
                notes = np.nan

            return pd.Series(
                [length_primary, length_max, packaging, notes],
                index=[
                    "Минимальная_длина",
                    "Максимальная_длина",
                    "Упаковка",
                    "Примечание_для_цены",
                ],
            )

        extracted_data = df[col_name].apply(extract_all_data)

        for col in extracted_data.columns:
            self.__df[col] = extracted_data[col]

    def __union_price_cols(self):
        """
        Объединяет и обрабатывает колонки связанные с ценой.
        """
        cols_with_price = [
            col for col in self.__df.columns if re.search(r"Цена, ", col)
        ]
        price_df = self.__df[cols_with_price]

        stacked_prices = price_df.stack()

        # Если цен вообще не нашлось, выходим, чтобы не было ошибок
        if stacked_prices.empty:
            self.__df["Цена"] = np.nan
            self.__df["Категория_цены"] = np.nan
            self.__df["Условие_цены"] = np.nan
            self.__df["Звоните"] = False
            self.__df.drop(columns=cols_with_price, inplace=True, errors="ignore")
            return

        final_prices = stacked_prices.reset_index()
        final_prices.columns = ["original_index", "Категория_цены", "temp_price"]

        final_prices = final_prices.drop_duplicates(
            subset="original_index", keep="last"
        )

        final_prices = final_prices.set_index("original_index")

        self.__df = self.__df.join(final_prices)

        PRICECOL = "Цена"
        CALLCOL = "Звоните"

        is_call = self.__df["temp_price"].str.lower() == "звоните"
        self.__df[CALLCOL] = is_call.fillna(False)

        self.__df.loc[self.__df[CALLCOL], "temp_price"] = np.nan

        pattern = r"^(?P<Цена>[\d\s.,]+)(?:\s+(?P<Условие_цены>.+))?$"
        extracted_data = self.__df["temp_price"].str.extract(pattern)

        self.__df[PRICECOL] = (
            extracted_data["Цена"] if not extracted_data.empty else np.nan
        )
        self.__df["Условие_цены"] = (
            extracted_data["Условие_цены"] if not extracted_data.empty else np.nan
        )

        self.__df[PRICECOL] = self.__df[PRICECOL].apply(
            lambda x: (
                float(str(x).replace(" ", "").replace(",", "."))
                if pd.notna(x)
                else np.nan
            )
        )

        self.__df["Категория_цены"] = self.__df["Категория_цены"].str.replace(
            "Цена, ", "", regex=False
        )

        self.__df.drop(
            columns=cols_with_price + ["temp_price"], inplace=True, errors="ignore"
        )

    def __preprocessing_size_col(self):
        """
        Обрабатывает колонку с размером
        """
        size_data = self.__df["Размер"].apply(PreProcessor.parse_size)
        size_df = pd.DataFrame(size_data.tolist(), index=self.__df.index)
        for col in size_df.columns:
            self.__df[col] = size_df[col]

    @staticmethod
    def parse_size(size_str):
        """
        Парсит сложное строковое значение из столбца "Размер"
        и возвращает словарь с извлеченными компонентами.
        """
        result = {}

        if pd.isna(size_str) or not str(size_str).strip():
            return result

        s = str(size_str).strip()
        s_clean = s.replace(",", ".").replace("х", "x")  # Унификация разделителей

        # Шаблон 1: Профили по ГОСТ/СТО (20К1, 16Б2, 24М, 40К5, 18К2В)
        match = re.fullmatch(r"(\d+)([А-Яа-я]+)(\d+)([А-Яа-я]?)", s, re.IGNORECASE)
        if match:
            result = {
                "Тип_продукции": "Профиль ГОСТ/СТО",
                "Типоразмер": int(match.group(1)),
                "Марка": f"{match.group(2).upper()}{match.group(3)}{match.group(4).upper()}",
            }
            return result

        # Шаблон 2: Европейские профили (IPE120, HE200A, UPN120)
        match = re.fullmatch(
            r"(IPE|HE|UPN|I|H|U)([A-Z]*)(\d+)([A-Z]*)", s, re.IGNORECASE
        )
        if match:
            result = {
                "Тип_продукции": "Европрофиль",
                "Марка": f"{match.group(1).upper()}{match.group(2)}{match.group(3)}{match.group(4)}",
                "Размер_A": float(match.group(3)),
            }
            return result

        # Шаблон 3: Рельсы (Р33, КР70)
        match = re.fullmatch(r"(Р|КР|К)(\d+)", s, re.IGNORECASE)
        if match:
            result = {
                "Тип_продукции": "Рельс",
                "Марка": f"{match.group(1).upper()}{match.group(2)}",
                "Типоразмер": int(match.group(2)),
            }
            return result

        # Шаблон 4: Профнастил/Сетки с префиксом (С20 0.5x1100(1150), ПН 28x27x0.5)
        match = re.match(r"^([А-Яа-я]+)\s+(.*)", s_clean)
        if match:
            prefix, rest = match.groups()
            result = {
                "Тип_продукции": "Профнастил/Сетка",
                "Марка": prefix,
                "Примечание_для_размера": rest,
            }
            return result

        # Шаблон 5: Электроды/Марки (Omnia-46 4, E308L-16 2х350)
        match = re.match(r"([A-Za-z]+-?\d+L?-\d*)\s*(.*)", s_clean)
        if match:
            return {
                "Тип_продукции": "Электрод/Марка",
                "Марка": match.group(1),
                "Примечание_для_размера": match.group(2) if match.group(2) else np.nan,
            }

        # Шаблон 6: Листовой/рулонный прокат с толщиной и размерами/диапазонами
        # (5 1500х6000, 0.5 9-1000, 508 1200x2000-3500)
        match = re.match(r"^([\d\.]+)\s+(.*)", s_clean)
        if match:
            potential_thickness, rest = match.groups()
            # Проверяем, что дальше идут размеры через 'x' или диапазон
            if "x" in rest or "-" in rest:
                result = {
                    "Тип_продукции": "Лист/Рулон",
                    "Толщина": float(potential_thickness),
                }

                range_match = re.search(r"([\d\.]+)-([\d\.]+)", rest)
                if range_match:
                    result["Диапазон_min"] = float(range_match.group(1))
                    result["Диапазон_max"] = float(range_match.group(2))
                    result["Примечание_для_размера"] = rest
                else:
                    dims = [float(d) for d in re.findall(r"[\d.]+", rest)]
                    if len(dims) > 0:
                        result["Размер_A"] = dims[0]
                    if len(dims) > 1:
                        result["Размер_B"] = dims[1]
                    if len(dims) > 2:
                        result["Размер_C"] = dims[2]

                return result

        # Шаблон 7: Габариты (100х50х4, 4x120)
        if "x" in s_clean:
            try:
                dims = [float(d) for d in re.findall(r"[\d.]+", s_clean)]
                result = {"Тип_продукции": "Габарит"}
                if len(dims) >= 1:
                    result["Размер_A"] = dims[0]
                if len(dims) >= 2:
                    result["Размер_B"] = dims[1]
                if len(dims) >= 3:
                    result["Размер_C"] = dims[2]
                return result
            except ValueError:
                # Не удалось преобразовать в числа, значит, это сложный случай
                pass

        # Шаблон 8: Число с буквой У/П (10У)
        match = re.fullmatch(r"(\d+\.?\d*)([УП])", s_clean, re.IGNORECASE)
        if match:
            return {
                "Тип_продукции": "Уголок/Полоса",
                "Размер_A": float(match.group(1)),
                "Марка": match.group(2).upper(),
            }

        # Шаблон 9: Дробь или сложный текст (33x11/30x2)
        if "/" in s_clean or re.search(
            r"[А-Яа-я]", s_clean
        ):  # Если есть слэш или кириллица
            return {"Тип_продукции": "Нестандартный", "Примечание_для_размера": s}

        # Шаблон 10: Простое число (последний вариант)
        try:
            return {"Тип_продукции": "Число", "Размер_A": float(s_clean)}
        except ValueError:
            return {"Тип_продукции": "Нераспознанный", "Примечание_для_размера": s}

    def __process_steel_col(self):
        """
        Обрабатывает колонку "Сталь", извлекая из неё новые полезные признаки.
        """
        self.__df.rename(columns={"Сталь": "Материал"}, inplace=True)
        material_clean = (
            self.__df["Материал"].str.lower().str.strip().fillna("не указан")
        )

        # --- Функция 1: Определяем тип материала ---
        def get_material_type(mat_str):
            if "aisi" in mat_str or re.search(r"\d*х\d+н\d+", mat_str):
                return "Нержавеющая сталь"
            if any(x in mat_str for x in ["амг", "ад", "д16", "в95", "ак4", "ак6"]):
                return "Алюминиевый сплав"
            if any(x in mat_str for x in ["лс", "л6"]):
                return "Латунь"
            if "бр" in mat_str:
                return "Бронза"
            if "чугун" in mat_str:
                return "Чугун"
            if "м1" in mat_str or "м2" in mat_str or "м3" in mat_str:
                return "Медь"
            if mat_str == "не указан":
                return "Не указан"
            return "Сталь"

        self.__df["Тип_материала"] = material_clean.apply(get_material_type)

        # --- Функция 2: Выделяем основную марку ---
        def get_primary_grade(mat_str):
            if mat_str == "не указан":
                return "не указан"
            parts = re.split(r"[\s/,-]+", mat_str)
            return parts[0]

        self.__df["Основная_марка"] = material_clean.apply(get_primary_grade)

        # --- Функция 3: Флаг свариваемости ---
        # Ищем марки вида А500С, С345С и т.д.
        self.__df["Свариваемость"] = material_clean.apply(
            lambda x: 1 if re.search(r"^(а|в|с)\d+с$", x) else 0
        )

    def __process_gost_col(self):
        """
        Обрабатывает колонку ГОСТ, извлекая из неё тип, номер и год стандарта.
        """
        col_name = "ГОСТ"
        if col_name not in self.__df.columns:
            return
        gost_series = (
            self.__df[col_name].fillna("не указан").str.upper().str.replace(" ", "")
        )
        pattern = re.compile(
            r"^(?P<type>[А-Я]+)(?P<number>[\d.-]+)(?:-(?P<year>\d{2,4}))?$"
        )
        extracted_data = gost_series.str.extract(pattern)
        extracted_data.columns = [
            "Тип_стандарта",
            "Номер_стандарта_raw",
            "Год_стандарта",
        ]
        self.__df["Тип_стандарта"] = extracted_data["Тип_стандарта"].fillna("не указан")
        self.__df["Номер_стандарта"] = extracted_data[
            "Номер_стандарта_raw"
        ].str.replace(r"-\d{2,4}$", "", regex=True)
        self.__df["Год_стандарта"] = (
            extracted_data["Год_стандарта"].astype(float).fillna(0).astype(int)
        )

    def save_data(self, path: str):
        """
        Сохранение данных в csv файл
        Args:
            path (str): абсолютный путь куда нужно сохранять данные
        """
        self.__df.to_csv(path)
