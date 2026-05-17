import asyncio
import pandas as pd
import os
from pathlib import Path
from parser_23MET import ParserSite_23MET
from proxyParser import ParserProxyLib
from preProcessor import PreProcessor
from update_config import change_update_config_json
import warnings


async def main(with_proxy=False):
    warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)
    RESULT_FILE_PATH = os.path.join(os.getcwd(), "23MET_DATA", "result.csv")
    PREPROCESSING_RESULT_FILE_PATH = os.path.join(
        os.getcwd(), "23MET_DATA", "preprocessing_result.csv"
    )

    print("Скрипт запущен!")
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    change_update_config_json(os.path.join(os.getcwd(), "config.json"))

    if with_proxy:
        proxy = ParserProxyLib(max_rate=100, time_period=1)
        await proxy.parsing(url_for_checking="https://23met.ru/")
        proxy_list = proxy.get_sockets()
        if not proxy_list:
            proxy_list = None
        main_parser = ParserSite_23MET(max_rate=100, proxy_list=proxy_list)
    else:
        main_parser = ParserSite_23MET(max_rate=100)
    df = await main_parser.run(
        with_update_sites_info=False,
        with_save_result=True,
        with_remove_intermediate_data=True,
    )

    if not os.path.exists(path=RESULT_FILE_PATH):
        print("Создаю файл:", RESULT_FILE_PATH)
        df.to_csv(RESULT_FILE_PATH)

    print("Начинаю предобработку данных")
    preprocessor = PreProcessor(csv_file_path=RESULT_FILE_PATH)

    print(
        "Закончился препроцессинг.\nНачинаю сохранять структурированные данные по пути:",
        PREPROCESSING_RESULT_FILE_PATH,
    )
    preprocessor.save_data(path=PREPROCESSING_RESULT_FILE_PATH)

    print("Работа закончилась")


if __name__ == "__main__":
    asyncio.run(main())
