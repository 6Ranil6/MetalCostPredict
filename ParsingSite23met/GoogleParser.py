import requests
import os
import re
import json
from bs4 import BeautifulSoup
import asyncio
from base import WorkerWithFiles
from base import Parser

class GoogleParser(Parser):

    def __init__(self, 
                 query_for_browser: str):
        """
        Args:
            query_for_browser (str): запрос браузеру.
        """
        self.__worker_with_files = WorkerWithFiles()
        self.__query = query_for_browser
        self.__scrapingant_url = "http://api.scraperapi.com" 
        self._api_key_path = os.path.join(os.getcwd(), 'config.json')
        DIR_NAME = "GoogleHTML"
        os.makedirs(DIR_NAME, exist_ok=True)
        self._dir_path = os.path.join(os.getcwd(), DIR_NAME) 

        self.__COST_ONE_REQUEST = 25 # стоимость кредитов на один запрос

    def _get_params(self, 
                    target_url: str) -> dict:
        """
        Возвращает параметры из config.json
        Args:
            target_url (str): URL-сайта, который нужно спарсить

        Returns:
            dict: возвращет словарь с target_url-ом и api-ключом. 
        """
        with open(self._api_key_path) as file:
            data = json.load(file)
        
        # Проверяем не кончились ли бесплатные запросы
        user_id = None
        for i in range(len(data['API_KEYS'])):
            if data['API_KEYS'][f'User_{i+1}']['MAX_CREDIT'] - data['API_KEYS'][f'User_{i+1}']['USED_CREDIT'] >= self.__COST_ONE_REQUEST:
                user_id = f"User_{i+1}"
                break
        if not user_id:
            print("У вас закончились бесплатные запросы на всех аккаунтах")
            return None

        self._user_id = user_id

        API_KEY = data['API_KEYS'][self._user_id]['API_KEY']

        return {'url' : target_url,
                'api_key' : API_KEY}

    def _increment_used_credit(self):
        """
        Увеличивает на определенное количество поле USED_CREDIT, которое отвечает за кол-во использованных кредитов в стороннем api - ScraperApi.
        """
        with open(self._api_key_path) as file:
            data = json.load(file)
        data['API_KEYS'][self._user_id]['USED_CREDIT'] += 1 * self.__COST_ONE_REQUEST
        with open(self._api_key_path, 'w') as file:
            json.dump(data, file, indent= 4, ensure_ascii= False)

    def save_data(self, num: int= 100, start: int= 0, stop: int= 100):
        """
        Сохраняет все сайты полученные Google-поиском. Запрос передавался при инициализации объекта.
        Args:
            num (int, optional): количество сайтов на одной странице в Google-поиске. Defaults to 100.
            start (int, optional): С какого сайта начинать по нумерации. Defaults to 0.
            stop (int, optional): На какой странице заканчивать поиск. Defaults to 100.
        """
        urls = ["https://www.google.com/search?q=" + self.__query + f"&num={num}&start={index}" for index in range(start, stop + 1, num)]

        counter = 0
        while not os.path.isfile(self._api_key_path):
            if counter == 5:
                break
            self._api_key_path = input(f"Введите путь к config.json файлу (осталось {5  - counter} попыток)")
            counter += 1
        
        for page_num, url in enumerate(urls, start= 1):
            params = self._get_params(url)
            response = requests.get(self.__scrapingant_url, params)

            # Обработка ответа
            if response.status_code == 200:
                print("Ответ получен успешно!")

                match = re.search(r"q=([^&]+)", url)
                if match:
                    filename_base = re.sub(r'[\\/*?:"<>|]', "", match.group(1))
                    filename = filename_base + str(page_num) + ".html"
                else:
                    filename = f"result_{page_num}.html"

                file_path = os.path.join(self._dir_path, filename)
                with open(file_path, 'w') as f:
                    f.write(response.text)
                print(f"Результаты сохранены в: {file_path}")
                self._increment_used_credit()
            else:
                print(f"Ошибка! Статус-код: {response.status_code}")
                print("Текст ошибки:", response.text)
    
    async def __get_file_and_parsing(self, file_path: str) -> list:
        """
        Чтение данных из файла и поиск ссылок
        Args:
            file_path (str): абсолютный путь к файлу
        Returns:
            list: Список всех ссылок на сайты
        """
        data = await self.__worker_with_files.get(file_path)
        soup = BeautifulSoup(data, 'lxml')
        sub_htmls = soup.find_all(name= 'span', class_ = "V9tjod")
        hrefs = []
        for sub_html in sub_htmls:
            sub_html: BeautifulSoup
            hrefs.append(sub_html.find('a').get('href'))
        return hrefs

    async def parsing(self):
        """
        Формирует файл ALL_HREFS.json, в котором храниться список всех ссылок.
        Returns:
            None
        """
        file_paths = [os.path.join(self._dir_path, file_name) for file_name in os.listdir(self._dir_path)]
        tasks = []
        for file_path in file_paths:
            task = asyncio.create_task(self.__get_file_and_parsing(file_path))
            tasks.append(task)
        results = [item for result in await asyncio.gather(*tasks) for item in result]
        await self.__worker_with_files._put_json_file(path= os.path.join(self._dir_path, 'ALL_HREFS.json'), data= results)

    async def run(self, num: int= 100, start: int= 0, stop: int= 100) -> None:
        """
        Сразу выполняет всю работу по сохранению данных из сайтов в директорию и забор всех ссылок из этих сайтов и сохранение в ALL_HREFS.json
        Args:
            num (int, optional): количество сайтов на одной странице в Google-поиске. Defaults to 100.
            start (int, optional): С какого сайта начинать по нумерации. Defaults to 0.
            stop (int, optional): На какой странице заканчивать поиск. Defaults to 100.
        Returns:
            None
        """
        self.save_data(num= num,
                       start= start,
                       stop= stop)
        await self.parsing()
    
    def get_urls(self) -> list:
        """
        Получение всех ссылок по запросу в браузер
        Returns:
            list: список ссылок
        """
        with open(os.path.join(self._dir_path, 'ALL_HREFS.json')) as file:
            urls = json.load(file)
        return urls
