from base import Parser
from GoogleParser import GoogleParser

import aiohttp
import asyncio
import aiolimiter
from bs4 import BeautifulSoup

import os
import re
import pandas as pd
import numpy as np
from typing import Union


class ParserSite_23MET(Parser):
    def __init__(
        self,
        base_url: str = "https://23met.ru",
        proxy_list: list = None,
        max_rate: int = 1,
        time_period: int = 10,
    ):
        """
        Args:
            base_url (str, optional): доменное имя сайта. Defaults to "https://23met.ru".
            proxy_list (list, optional): Список прокси адресов. Defaults to None.
            max_rate (int, optional): Количество запросов за time_period. Defaults to 1.
            time_period (int, optional): Время за которое выполняется max_rate запросов. Defaults to 10.
        """

        super().__init__(base_url, proxy_list)
        self.__limiter = aiolimiter.AsyncLimiter(
            max_rate=max_rate, time_period=time_period
        )
        DIR_NAME = "23MET_DATA"
        os.makedirs(DIR_NAME, exist_ok=True)
        self._dir_path = os.path.join(os.getcwd(), DIR_NAME)
        self.__file_paths = None
        self.__unique_columns_name = None

    async def __get_and_save_site_data(
        self, session: aiohttp.ClientSession, url: str, accept: str
    ) -> None:
        """
        Получение html страницы и ее сохранение в файл
        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.
        Returns:
            None
        """
        data = await self.get_html(session=session, url=url, accept=accept)
        if self.__checking(data):
            file_path = os.path.join(self._dir_path, url.split("/")[-1] + ".html")
            await self.put_file(path=file_path, data=data)

    async def __process_single_url_with_limiter(
        self, session: aiohttp.ClientSession, url: str, accept: str
    ) -> None:
        """
        Получение html страницы и ее сохранение в файл, но с ограничением по количеству запросов за определенное время. Настройка кол-ва запросов за определенное время производится при инициализации объекта, с помощью параметров max_rate и time_period.
        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.
        Returns:
            None
        """
        async with self.__limiter:
            await self.__get_and_save_site_data(session=session, url=url, accept=accept)

    def __checking(self, html: str) -> bool:
        """
        Проверяет подходящий ли сайт или нет
        Args:
            html (str): код html страницы

        Returns:
            bool: True- подходит, False - неподходит
        """
        try:
            soup = BeautifulSoup(html, "lxml")
        except TypeError:
            print(html, "тип None")
            return False
        title_tag = soup.find("title")
        if title_tag is not None and re.search(
            r"прайс-лист — 23MET.ru\Z", soup.find("title").text
        ):
            return True
        return False

    async def save_data(
        self,
        accept: str = "*/*",
        with_update_sites_info: bool = False,
        num: int = 100,
        start: int = 0,
        stop: int = 100,
    ) -> None:
        """
        Получает данные со всех сайтов (выданных Google-поиском) и сохраняет их в файлы
        Args:
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'
            with_update_sites_info (bool, optional): Просто обновить все сайты или полностью спарсить и Google-поиск?. Defaults to False.
            num (int, optional): Кол-во сайтов отображаемое Googl-ом на одной ее html странице . Defaults to 100.
            start (int, optional): С какого сайта начать отображать страницы в Google поиске. Defaults to 0.
            stop (int, optional): На каком сайте закончить отображать страницы в Google поиске. Defaults to 100.
        Returns:
            None
        """

        google_searcher = GoogleParser(query_for_browser="site:23met.ru прайс-лист")
        if with_update_sites_info:
            await google_searcher.run(num=num, start=start, stop=stop)
        else:
            await google_searcher.parsing()

        urls = google_searcher.get_urls()

        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                task = asyncio.create_task(
                    self.__process_single_url_with_limiter(
                        session=session, url=url, accept=accept
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def __get_one_site_unique_columns_name(
        self, file_path: str
    ) -> Union[None, set]:
        """
        Ищет уникальное название колонки для одного сайта(file_path)
        Args:
            file_path (str): абсолютный путь к файлу

        Returns:
            Union[None, set]: Если None, то не нашлось уникальных названий колонок
        """

        html = await self.get_file(file_path)
        unique_column_names = set()
        if self.__checking(html):
            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table", "tablesorter")
            for table in tables:
                table: BeautifulSoup
                columns_name = table.find("thead").find_all("th")
                for column_name in columns_name:
                    unique_column_names.add(column_name.text)
            return unique_column_names
        else:
            return None

    async def __get_all_unique_columns_name(self) -> list:
        """
        Возвращает список всех уникальных названий колонок со всех сайтов
        Returns:
            list: список всех уникальных названий колонок со всех сайтов
        """
        tasks = []
        if not self.__file_paths:
            print("Не был инициализирован self.__file_paths. Создаю его сам")
            file_names = os.listdir(self._dir_path)
            self.__file_paths = [
                os.path.join(self._dir_path, file_name) for file_name in file_names
            ]

        for file_path in self.__file_paths:
            tasks.append(
                asyncio.create_task(self.__get_one_site_unique_columns_name(file_path))
            )
        results = [result for result in await asyncio.gather(*tasks) if result]
        return list({item for result in results for item in result})

    async def _parsing_one_site(self, file_path: str) -> Union[None, dict]:
        """
        Парсит 1 сайт(в file_path)
        Args:
            file_path (str): абсолютный путь к файлу

        Returns:
            Union[None, dict]: Если None, то не удалось спарсить сайт. dict - данные, которые удалось спарсить
        """
        html = await self.get_file(file_path)
        data = dict()
        if not self.__unique_columns_name:
            print(
                "Переменная self.__unique_columns_name не была инициализирована. Инициализирую ее!"
            )
            self.__unique_columns_name = await self.__get_all_unique_columns_name()
        for column_name in self.__unique_columns_name:
            data[column_name] = []

        if self.__checking(html):
            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table", "tablesorter")

            for table in tables:
                table: BeautifulSoup
                columns_name = [
                    column.text for column in table.find("thead").find_all("th")
                ]
                trS_in_tbody = table.find("tbody").find_all("tr")
                for tr_in_tbody in trS_in_tbody:
                    tdS_in_tbody = tr_in_tbody.find_all("td")
                    for column_name, td_in_tbody in zip(columns_name, tdS_in_tbody):
                        if td_in_tbody.text == "":
                            data[column_name].append(None)
                        else:
                            data[column_name].append(td_in_tbody.text)

                    for unique_column_name in self.__unique_columns_name:
                        if unique_column_name not in columns_name:
                            data[unique_column_name].append(None)
            return data

        else:
            return None

    def __delete_intermediate_data(self) -> None:
        """
        Удаление ненужных/промежуточных файлов

        Returns:
            None
        """
        for file_path in self.__file_paths:
            os.remove(file_path)

    async def parsing(self, with_save_result: bool = True) -> pd.DataFrame:
        """
        Парсинг данных из сайтов.
        Args:
            with_save_result (bool, optional): Сохранить ли результат в csv файл?. Defaults to True.

        Returns:
            pd.DataFrame: DataFrame - в котором храниться все спарщенные данные
        """
        file_names = os.listdir(self._dir_path)
        self.__file_paths = [
            os.path.join(self._dir_path, file_name) for file_name in file_names
        ]
        self.__unique_columns_name = await self.__get_all_unique_columns_name()
        data = dict()
        for column_name in self.__unique_columns_name:
            data[column_name] = []

        main_df = pd.DataFrame(data)
        tasks = []
        for file_path in self.__file_paths:
            tasks.append(asyncio.create_task(self._parsing_one_site(file_path)))
        results = await asyncio.gather(*tasks)

        sites_without_needing_data = []
        df_s = dict()
        for index, result in enumerate(results):
            if not result:
                sites_without_needing_data.append(self.__file_paths[index])
            else:
                try:
                    df_s[self.__file_paths[index]] = pd.DataFrame(data=result)
                except ValueError:
                    print("Не все масивы одной длинны тут:", self.__file_paths[index])
        files_not_parsing = [
            os.path.join(self._dir_path, "result.csv"),
            os.path.join(self._dir_path, "preprocessing_result.csv"),
        ]
        if sites_without_needing_data:
            print(
                "Эти сайты не подходят под шаблон парсинга:",
                [
                    site
                    for site in sites_without_needing_data
                    if site not in files_not_parsing
                ],
            )

        main_df = pd.concat(list(df_s.values()), ignore_index=True)
        main_df = main_df.sort_values(by="Наименование", ignore_index=True)
        if with_save_result:
            temp_file_path = os.path.join(self._dir_path, "result.csv")

            if os.path.isfile(temp_file_path):
                temp_df = pd.read_csv(temp_file_path, index_col=0)
                main_df = pd.concat([main_df, temp_df], axis=0)
                main_df.drop_duplicates(inplace=True)
                main_df.reset_index(inplace=True)
                main_df.drop(columns=["index"], inplace=True)
                for column in main_df.columns:
                    main_df[column] = main_df[column].replace([" ", ""], np.nan)
            main_df.to_csv(temp_file_path)

        return main_df

    async def run(
        self,
        accept: str = "*/*",
        num: int = 100,
        start: int = 0,
        stop: int = 100,
        with_update_sites_info: bool = False,
        with_save_result: bool = True,
        with_remove_intermediate_data: bool = False,
    ) -> pd.DataFrame:
        """
        Основной метод, после запуска которого выполнятся все необходимые методы в нужной последовательности, а именно:
        1) Сохранение всех данных из html страниц в файлы
        2) Забор нужной информации из этих файлов
        3) При необходимости удаление промежуточных файлов

        Args:
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'
            with_update_sites_info (bool, optional): Просто обновить все сайты или полностью спарсить и Google-поиск?. Defaults to False.
            num (int, optional): Кол-во сайтов отображаемое Googl-ом на одной ее html странице . Defaults to 100.
            start (int, optional): С какого сайта начать отображать страницы в Google поиске. Defaults to 0.
            stop (int, optional): На каком сайте закончить отображать страницы в Google поиске. Defaults to 100.
            with_save_result (bool, optional): Сохранить результат в файл?. Defaults to True.
            with_remove_intermediate_data (bool, optional): Удалить промежуточные файлы?. Defaults to False.

        Returns:
            pd.DataFrame
        """

        print("Начинаю процесс скачивания данных с сайта")
        await self.save_data(
            accept=accept,
            with_update_sites_info=with_update_sites_info,
            num=num,
            start=start,
            stop=stop,
        )

        print("Начинаю процесс забора данных со скаченных сайтов")
        main_df = await self.parsing(with_save_result=with_save_result)

        if with_remove_intermediate_data:
            print("Удаляю все промежуточные данные")
            self.__delete_intermediate_data()

        return main_df
