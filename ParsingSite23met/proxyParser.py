from base import Parser
import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
import re
import json
import aiolimiter
from typing import Union


class ParserProxyLib(Parser):
    def __init__(
        self,
        base_url: str = "https://proxylib.com/free-proxy-list",
        max_rate: int = 1,
        time_period: int = 10,
    ):
        """
        Args:
            base_url (str, optional): url по которому будет парситься proxies. Defaults to "https://proxylib.com/free-proxy-list".
            max_rate (int, optional): Количество запросов за time_period. Defaults to 1.
            time_period (int, optional): Время за которое выполняется max_rate запросов. Defaults to 10.
        """
        super().__init__(base_url, proxy_list=None)
        self.__dir_path = None
        self.__limiter = aiolimiter.AsyncLimiter(
            max_rate=max_rate, time_period=time_period
        )

    async def _fetch_and_save_site(
        self,
        name_file: str,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore,
        accept: str = "*/*",
    ) -> None:
        """
        Делает запрос по url-у и сохраняет полученный  html в name_file
        Args:
            name_file (str): имя файла
            session (aiohttp.ClientSession): Сессия
            url (str): url
            semaphore (asyncio.Semaphore, optional): нужен для ограничения количества запросов. Defaults to None.
            accept (str, optional): типы файлов, которые клиент может принять (отображается браузером в header-e). Defaults to '*/*'.
        """
        html = await self.get_html(
            session=session, url=url, semaphore=semaphore, accept=accept
        )

        file_path = os.path.join(self.__dir_path, name_file)
        if html:
            await self.put_file(path=file_path, data=html)
            print(f"Сохранил данные с {url} в {file_path}")
        else:
            print(f"Не удалось скачать с {url}")

    def __delete_all_page_files(self, MAX_PAGES: int) -> None:
        """
        Удаляет все ненужные скаченные файлы из которых были забраны данные
        Args:
            MAX_PAGES (int): количество страниц
        """
        for page_num in range(MAX_PAGES + 1):
            name_file = f"Page{page_num}.html"
            os.remove(os.path.join(self.__dir_path, name_file))

    async def _GET_socket_and_type(self, file_path: str) -> list:
        """
        Сразу парсит и сокеты и тип соединения из file_path
        Args:
            file_path (str): абсолютный путь к файлу

        Returns:
            list: возвращает список кортежей, имеющие структуры (ТИП СОЕДИНЕНИЯ, СОКЕТ)
        """
        html = await self.get_file(path=file_path)
        soup = BeautifulSoup(html, "lxml")
        data_list = soup.find_all(name="td")
        sockets = []
        types = []

        for data in data_list:
            data: BeautifulSoup
            a_tag_with_onclick = data.find(name="a", onclick=True)

            try:
                a_tag_title = data.find(name="a")["title"]
            except:
                a_tag_title = None

            if a_tag_with_onclick:
                match = re.search(
                    pattern=r"copyToClipboard", string=a_tag_with_onclick["onclick"]
                )
                # match = re.search(pattern=)
                if match:
                    sockets.append(a_tag_with_onclick.get_text().strip())

            if a_tag_title:
                match = re.match(pattern=r"Free", string=a_tag_title)
                if match:
                    types.append(a_tag_title.split()[1])

        return zip(types, sockets)

    def _create_dir(self, dir_name: str = "PROXY"):
        """
        Создаем директорию в которой будем сохранять все данные
        Args:
            dir_name (str, optional): название директории. Defaults to "PROXY".
        """
        self.__dir_path = os.path.join(os.getcwd(), dir_name)

        if not os.path.isdir(self.__dir_path):
            os.mkdir(self.__dir_path)

    async def parsing(
        self,
        dir_name: str = "PROXY",
        CONECTION_PROTOCOL_TYPE: str = "https",
        MAX_PAGES: int = 77,
        MAX_TASKS: int = 25,
        delete_all_page_files: bool = True,
        url_for_checking: Union[None, str] = None,
    ) -> None:
        """
        Основрая функция для парсинга PROXY серверов по типу соединения.
        Args:
            dir_name (str, optional): Название директории, в котором сохраняются данные. Defaults to "PROXY".
            CONECTION_PROTOCOL_TYPE (str, optional): Тип соединения. Defaults to 'https'.
            MAX_PAGES (int, optional): Количество страниц необходимое для забора proxy серверов из сайта. Defaults to 77.
            MAX_TASKS (int, optional): Максимальное количество параллельных запросов на сайт. Defaults to 25.
            delete_all_page_files (bool, optional): Удалять ли ненужные файлы с данными?. Defaults to True.
            url_for_checking (Union[None, str], optional): По какому URL-у проверить работоспосообность proxy-серверов. Defaults to None.
        """
        self._create_dir(dir_name)

        semaphore = asyncio.Semaphore(MAX_TASKS)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            page_num = 1
            for page_num in range(MAX_PAGES + 1):
                url = self.base_url + f"/?proxy_page={page_num}"
                name_file = f"Page{page_num}.html"

                task = asyncio.create_task(
                    self._fetch_and_save_site(
                        name_file=name_file,
                        session=session,
                        url=url,
                        semaphore=semaphore,
                        accept="*/*",
                    )
                )  # Скачиваем данные с сайта

                tasks.append(task)

            print(
                "Запускаю задачи на чтение всех страниц сайта и сохрание всего в файлы!"
            )
            await asyncio.gather(*tasks)

            tasks2 = []
            for page_num in range(MAX_PAGES + 1):
                name_file = f"Page{page_num}.html"
                task2 = asyncio.create_task(
                    self._GET_socket_and_type(
                        file_path=os.path.join(self.__dir_path, name_file)
                    )
                )  # Вынимаем данные из сайта
                tasks2.append(task2)

            print(f"Запускаю парсинг сокетов и их типов({CONECTION_PROTOCOL_TYPE})")

            json = {CONECTION_PROTOCOL_TYPE.upper(): []}
            for pair in await asyncio.gather(*tasks2):
                for t, s in pair:
                    if t == CONECTION_PROTOCOL_TYPE.upper():
                        json[t].append(f"{CONECTION_PROTOCOL_TYPE.lower()}://" + s)

            self.__proxies = json[CONECTION_PROTOCOL_TYPE.upper()]
            if json:

                if url_for_checking:
                    tasks = []
                    for proxy in self.__proxies:
                        task = asyncio.create_task(
                            self.checking(url=url_for_checking, proxy=proxy)
                        )
                        tasks.append(task)
                    results = await asyncio.gather(*tasks)
                    working_proxies = [
                        proxy
                        for proxy, is_working in zip(self.__proxies, results)
                        if is_working
                    ]
                    json[CONECTION_PROTOCOL_TYPE.upper()] = working_proxies
                    await self._save_data_in_json_file(
                        path=os.path.join(self.__dir_path, "proxy.json"), data=json
                    )
                else:
                    # сохраняем JSON в файл: "proxy.json"
                    await self._save_data_in_json_file(
                        path=os.path.join(self.__dir_path, "proxy.json"), data=json
                    )
                print("Все завершилось успешно!")
            else:
                print(f"Не нашлось PROXY с {CONECTION_PROTOCOL_TYPE}")

        if delete_all_page_files:
            print("Удаляю все промежуточные данные!")
            self.__delete_all_page_files(MAX_PAGES=MAX_PAGES)

        update_json = {
            "base_url": self.base_url,
            "dir_name": dir_name,
            "CONECTION_PROTOCOL_TYPE": CONECTION_PROTOCOL_TYPE.upper(),
            "MAX_PAGES": MAX_PAGES,
            "MAX_TASKS": MAX_TASKS,
            "delete_all_page_files": delete_all_page_files,
        }

        await self._save_data_in_json_file(
            path=os.path.join(dir_name, "update_setting.json"), data=update_json
        )

    def get_sockets(self) -> list:
        """
        Возвращает сокеты, используется метод после метода parsing()
        Returns:
            list: список сокетов
        """
        if not self.__dir_path or not os.path.exists(self.__dir_path):
            print(
                "Ошибка: директория с прокси не найдена. Возможно, метод parsing() не был вызван."
            )
            return []
        try:
            protocol_type = None
            with open(
                file=os.path.join(self.__dir_path, "update_setting.json")
            ) as file:
                protocol_type = json.load(file)["CONECTION_PROTOCOL_TYPE"]
        except AttributeError:
            self._create_dir()
            with open(
                file=os.path.join(self.__dir_path, "update_setting.json")
            ) as file:
                protocol_type = json.load(file)["CONECTION_PROTOCOL_TYPE"]
        with open(file=os.path.join(self.__dir_path, "proxy.json")) as f:
            return json.load(f)[protocol_type]

    async def checking(self, proxy: str, url: str) -> bool:
        """
        Метод для проверки работоспособности переданново вами proxy для сайта по URL
        Args:
            proxy (_type_): один proxy
            url (str): по которому нужно проверить работоспособность прокси

        Returns:
            bool: True - прокси работает, False - прокси не работает
        """
        try:
            async with self.__limiter:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url=url, proxy=proxy, ssl=False) as response:
                        if response.status == 200:
                            print(f"{proxy} работает!!!")
                            return True
                        else:
                            print(f"{proxy} НЕ работает!!!")
                            return False

        except aiohttp.ClientProxyConnectionError as e:
            print(
                f"Ошибка подключения к прокси: {e}. Проверьте адрес, порт, логин или пароль."
            )
            return False
        except aiohttp.ClientHttpProxyError as e:
            print(
                f"Ошибка HTTP от прокси (например, 407 Proxy Authentication Required): {e}"
            )
            return False
        except asyncio.TimeoutError:
            print("Ошибка! Прокси не ответил за 10 секунд (Таймаут).")
            return False
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            return False
