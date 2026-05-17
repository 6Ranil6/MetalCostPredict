from abc import ABC, abstractmethod
import aiohttp
import asyncio
from fake_useragent import UserAgent
from typing import Any, Union
import aiofiles
import json
import random


class WorkerWithHtml:
    """
    Класс, в котором реализуется работа с HTML-страницей.
    Основной функционал забрать данные из сайта с помощью метода get().

    """

    def __init__(self, proxy_list: list = None):
        super().__init__()
        self._user = UserAgent().random

        if proxy_list:
            self.__is_exists_proxy = True
            self.__proxies = proxy_list
        else:
            self.__is_exists_proxy = False

    @property
    def user(self):
        return self._user

    async def __get_with_proxy(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore = None,
        accept: str = "*/*",
    ) -> Union[None, str]:
        """
        Забрать данные из сайта с помощью тех прокси серверов, которые были переданы в объект при инициализации.
        (Параметр: proxy_list)
        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            semaphore (asyncio.Semaphore, optional): нужен для ограничения количества запросов. Defaults to None.
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.

        Returns:
            Union[None, str]: None или HTML-разметка ввиде строки
        """

        async def read_data_in_site(proxy=None, header=None):
            """
            Основной Метод для забора данных из сайта с использование proxy
            """
            nonlocal data

            kwargs = {"url": url, "headers": header}
            if proxy:
                kwargs["proxy"] = proxy

            try:
                # Чтение данных из сайта
                async with session.get(**kwargs) as response:

                    data = await response.text()
                    if "Слишком много запросов" in data:
                        print("Блокировка! Пробуем сменить User-agent и PROXY...")
                        return False
                    else:
                        return True

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Ошибка при работе с прокси {proxy}: {e}")
                return False

        header = {
            "Accept": accept,
            "User-Agent": self._user,
            "Accept-Language": "ru,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Referer": "https://23met.ru/",
        }

        data = None
        success = None
        if not self.__is_exists_proxy:
            print("Вы не передавали список с прокси серверами при объявлении класса")
            return None

        for proxy in self.__proxies:
            local_header = header.copy()
            local_header["User-Agent"] = UserAgent().random

            if semaphore:
                async with semaphore:
                    success = await read_data_in_site(proxy, local_header)

            else:
                success = await read_data_in_site(proxy, local_header)

            if success:
                await asyncio.sleep(random.uniform(2, 5))
                return data

        else:
            print("Не нашлось PROXY сервер, который работает исправно!")
            return None

    async def __get_without_proxy(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore = None,
        accept: str = "*/*",
    ) -> Union[None, str]:
        """
        Метод для забора данных из сайта, но без использования proxy_list. Используется, когда proxy_list = None

        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            semaphore (asyncio.Semaphore, optional): нужен для ограничения количества запросов. Defaults to None.
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.
        Raises:
            Exception: сообщение о блокировки сайтом нашего IP.

        Returns:
            Union[None, str]: None или HTML-разметка ввиде строки
        """

        header = {
            "Accept": accept,
            "User-Agent": self._user,
            "Accept-Language": "ru,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        async def read_data_in_site():
            """
            Основной Метод для чтения данных из сайта
            """
            data = None
            if semaphore:
                async with semaphore:
                    # Чтение данных из сайта
                    async with session.get(url=url, headers=header) as response:
                        data = await response.text()

            else:
                # Чтение данных из сайта
                async with session.get(url=url, headers=header) as response:
                    data = await response.text()
            if "Слишком много запросов" in data:
                print("Блокировка (без прокси)! Сайт требует капчу или ввел лимиты.")
                # Здесь мы не можем просто вернуть False, т.к. нет цикла перебора.
                # Лучше всего "упасть", чтобы показать, что без прокси дальше нельзя.
                raise Exception("Сайт заблокировал наш IP. Пройдите капчу.")

            return data

        data = await read_data_in_site()
        await asyncio.sleep(random.uniform(2, 5))
        return data

    async def get(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore = None,
        accept: str = "*/*",
    ) -> Union[None, str]:
        """
        Метод выполняет основное предназначение всего класса. Служит для забора данных из сайта переданного по URL, учитывает и сессию(которая хранит в себе все данные об авториазации и куки)
        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            semaphore (asyncio.Semaphore, optional): нужен для ограничения количества запросов. Defaults to None.
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.
        Returns:
            Union[None, str]: None или HTML-разметка
        """
        if self.__is_exists_proxy:
            return await self.__get_with_proxy(
                session=session, url=url, semaphore=semaphore, accept=accept
            )
        else:
            return await self.__get_without_proxy(
                session=session, semaphore=semaphore, url=url, accept=accept
            )


class WorkerWithFiles:
    """
    Класс предназначен для работы с файлами.
    Умеет забирать данные из файлов / Сохранять данные в файл / Сохранять данные в виде json-ов в файл.
    """

    def __init__(self):
        super().__init__()

    async def get(self, path: str) -> str:
        """
        Забор данных из файла по пути path.
        Args:
            path (str): абсолютный путь к файлу
        Returns:
            str: данные из файла
        """
        data = None
        async with aiofiles.open(file=path) as file:
            data = await file.read()
        return data

    async def put(self, path: str, data: Any) -> None:
        """
        Метод кладет данные по абсолютному пути
        Args:
            path (str): абсолютный путь к файлу
            data (Any): данные, которые нужно положить
        """
        async with aiofiles.open(file=path, mode="w") as file:
            await file.write(data)

    async def _put_json_file(
        self, path: str, data: Union[dict, list]
    ) -> None:  # изменил ANY  на Union[dict, list]
        """
        Метод кладет json по абсолютному пути path.
        Args:
            path (str): абсолютный путь к файлу
            data (Union[dict, list]): данные, которые нужно положить
        """
        async with aiofiles.open(path, "w") as file:
            json_str = json.dumps(obj=data, indent=4, ensure_ascii=False)
            await file.write(json_str)

    @staticmethod
    def get_no_async(file_path: str) -> str:
        """
        Получение данных не асинхронным способом.
        Args:
            file_path (str): абсолютный путь к файлу
        """
        with open(file_path) as file:
            return file.read()


class Parser(ABC):
    """
    Абстрактный класс для парсинга любого сайта.
    """

    def __init__(self, base_url: str, proxy_list: list = None):
        """
        Args:
            base_url (str): доменное имя сайта
            proxy_list (list, optional): список прокси, если proxy_list = None, то прокси не будет использоваться, вместо этого при парсинге будет использоваться ваш IP:ПОРТ. Defaults to None.
        """
        self.__file_worker = WorkerWithFiles()
        self.__html_worker = WorkerWithHtml(proxy_list)
        self.base_url = base_url

    @abstractmethod
    def parsing(self):
        pass

    @property
    def user_agent(self):
        return self.__html_worker.user

    async def put_file(self, path: str, data: Any) -> None:
        """
        Кладет данные в файл
        Args:
            path (str): абсолютный путь
            data (Any): данные
        """
        await self.__file_worker.put(path=path, data=data)

    async def get_file(self, path: str) -> str:
        """
        Берет данные из файла
        Args:
            path (str): абсолютный путь к файлу

        Returns:
            str
        """
        return await self.__file_worker.get(path=path)

    @staticmethod
    def get_data_in_file_no_async(file_path: str) -> str:
        """
        Получение данных из файла не асинхронным способом
        Args:
            file_path (str): абсолютный путь к файлу

        Returns:
            str
        """
        return WorkerWithFiles.get_no_async(file_path=file_path)

    async def get_html(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore = None,
        accept: str = "*/*",
    ) -> Union[None, str]:
        """
        Получение данных из сайта по переданному вами URL-у.
        Args:
            session (aiohttp.ClientSession): Сессия
            url (str): url
            semaphore (asyncio.Semaphore, optional): нужен для ограничения количества запросов. Defaults to None.
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.

        Returns:
            Union[None, str]: None если данных нет или не удалось скачать данные из сайта. str - данные из сайта в виде строки
        """
        retries = 5  # количество попыток при неудачном запросе
        for _ in range(retries):
            try:
                return await self.__html_worker.get(
                    session=session, url=url, semaphore=semaphore, accept=accept
                )
            except:
                print("Не вернулся ответ от сервера, пробую еще раз!")
            await asyncio.sleep(2)
        print(f"Не удалось получить данные с {url} после {retries} попыток. Пропускаю.")
        return None

    async def _save_data_in_json_file(self, path: str, data: Any) -> None:
        """
        Метод кладет json по абсолютному пути path.
        Args:
            path (str): абсолютный путь к файлу
            data (Union[dict, list]): данные, которые нужно положить
        """
        await self.__file_worker._put_json_file(path, data)
