import logging
import os
import time

from http import HTTPStatus
from sys import stdout

import requests
import telegram

from dotenv import load_dotenv

import exceptions as exp

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

LOG_MESSAGES = {
    'missed_env': 'Отсутствуют переменные окружения',
}


def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp=int(time.time())) -> dict:
    # current_timestamp = 0
    params = {'from_date': current_timestamp}
    #params = {}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    answer_code = homework_statuses.status_code
    if answer_code is not HTTPStatus.OK:
        message = f'API Yandex практикума вернул код {answer_code}'
        raise exp.API_Yandex_Practcum_Exception(message)

    return dict(homework_statuses.json())


def check_response(response) -> dict:
    if response['homeworks']:
        return response['homeworks']

    return dict()


def parse_status(homework) -> str:
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка переменных окружения"""

    check_env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    result = True
    for var, val in check_env_vars.items():
        if val is None:
            result = False
            logging.critical(f'Отсутствует переменная окружения: {var}')

    return result


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            for homework in check_response(response):
                message = parse_status(homework)
                send_message(bot, message)
                logging.info(f'сообщение успешно отправлено {message}')
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except exp.API_Yandex_Practcum_Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=stdout,
        level=logging.DEBUG,
    )

    main()
