from datetime import datetime
import json

def change_update_config_json(file_path: str) -> None:
    """
    Функция отвечающая за обновление данных в config.json. Используется для контроля кол-ва кредитов для ScraperApi
    Args:
        file_path (str): абсолютный путь к файлу
    """
    UPDATE = 'UPDATE'
    LAST_CHECKING_DATE = 'LAST_CHECKING_DATE'
    NEXT_UPDATE = 'NEXT_UPDATE'
    API_KEYS = 'API_KEYS'
    USER_ID = 'User_'
    COUNT_USER = 7
    USED_CREDIT = 'USED_CREDIT'
    Format = r"%Y-%m-%d"

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            json_ = json.load(file)
    except Exception as e:
        print(f"Не удалось прочитать файл {file_path}: {e}")
        return

    last_check_str = json_[UPDATE][LAST_CHECKING_DATE]
    today_str = datetime.today().strftime(format=Format)

    last_check_date = datetime.strptime(last_check_str, Format).date()
    today_date = datetime.strptime(today_str, Format).date()
    
    if last_check_date >= today_date:
        print("Проверка сегодня уже проводилась.")
        return
        
    days_passed = (today_date - last_check_date).days
    current_next_update = json_[UPDATE][NEXT_UPDATE]
    
    print(f"Прошло дней с последней проверки: {days_passed}")
    
    if current_next_update <= days_passed or days_passed >= 30:
        print("Время сброса кредитов!")
        for i in range(1, COUNT_USER + 1):
            json_[API_KEYS][USER_ID + str(i)][USED_CREDIT] = 0
        json_[UPDATE][NEXT_UPDATE] = 30
    else:
        print("Уменьшаем счетчик дней до обновления.")
        json_[UPDATE][NEXT_UPDATE] = current_next_update - days_passed

    json_[UPDATE][LAST_CHECKING_DATE] = today_str
    
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(json_, file, indent=4, ensure_ascii= False) 
